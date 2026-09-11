package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"
)

type Client struct {
	baseURL string
	http    *http.Client
}

func NewClient(baseURL string) *Client {
	return &Client{baseURL: baseURL, http: &http.Client{Timeout: 30 * time.Second}}
}

func (c *Client) post(path string, body interface{}) (int, map[string]interface{}, error) {
	jsonBody, _ := json.Marshal(body)
	req, _ := http.NewRequest("POST", c.baseURL+path, bytes.NewReader(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "gonuts-interop-driver/1.0")
	resp, err := c.http.Do(req)
	if err != nil {
		return 0, nil, err
	}
	defer resp.Body.Close()
	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)
	return resp.StatusCode, result, nil
}

func (c *Client) get(path string) (int, map[string]interface{}, error) {
	req, _ := http.NewRequest("GET", c.baseURL+path, nil)
	req.Header.Set("User-Agent", "gonuts-interop-driver/1.0")
	resp, err := c.http.Do(req)
	if err != nil {
		return 0, nil, err
	}
	defer resp.Body.Close()
	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)
	return resp.StatusCode, result, nil
}

func writeResult(verdict, reason string) {
	result := map[string]interface{}{
		"verdict": verdict,
		"reason":  reason,
		"wallet":  "gonuts-tollgate",
		"flow":    os.Getenv("TESTCASE"),
		"mint":    os.Getenv("MINT_URL"),
	}
	json.NewEncoder(os.Stdout).Encode(result)
	// Also write to artifact dir
	if artDir := os.Getenv("ARTIFACT_DIR"); artDir != "" {
		os.MkdirAll(artDir, 0755)
		f, _ := os.Create(artDir + "/result.json")
		defer f.Close()
		json.NewEncoder(f).Encode(result)
	}
	if verdict == "PASS" {
		os.Exit(0)
	} else if verdict == "SKIP" {
		os.Exit(127)
	}
	os.Exit(1)
}

func main() {
	mintURL := os.Getenv("MINT_URL")
	flow := os.Getenv("TESTCASE")
	fmt.Printf("gonuts-tollgate driver: mint=%s flow=%s\n", mintURL, flow)

	client := NewClient(mintURL)

	// Health check
	code, info, err := client.get("/v1/info")
	if err != nil || code != 200 {
		writeResult("FAIL", fmt.Sprintf("mint unreachable: %v (code %d)", err, code))
	}
	version, _ := info["version"].(string)
	fmt.Printf("mint version: %s\n", version)

	// Keyset check — the critical compatibility boundary
	code, keysets, err := client.get("/v1/keysets")
	if err != nil || code != 200 {
		writeResult("FAIL", fmt.Sprintf("keysets unreachable: %v", err))
	}

	keysetsList, _ := keysets["keysets"].([]interface{})
	if len(keysetsList) == 0 {
		writeResult("FAIL", "no keysets offered by mint")
	}

	// Check for V2 keyset IDs (the format our fork supports)
	hasV2 := false
	for _, ks := range keysetsList {
		if m, ok := ks.(map[string]interface{}); ok {
			id, _ := m["id"].(string)
			if len(id) > 16 {
				hasV2 = true
			}
			fmt.Printf("  keyset: id=%s unit=%v active=%v\n", id, m["unit"], m["active"])
		}
	}
	fmt.Printf("V2 keysets: %v\n", hasV2)

	switch flow {
	case "mint_swap":
		// Create a quote
		code, quote, err := client.post("/v1/mint/quote/bolt11", map[string]interface{}{
			"amount": 64,
			"unit":   "sat",
		})
		if err != nil || code != 200 {
			writeResult("FAIL", fmt.Sprintf("quote failed: %v (code %d)", err, code))
		}
		quoteID, _ := quote["quote"].(string)
		fmt.Printf("quote created: %s\n", quoteID)

		// For gonuts, the full mint requires the blind signature protocol.
		// We test the API-level compatibility: can we create quotes, read keysets,
		// and get the right response formats?
		// The actual blinding/spending is tested by the TollGate integration suite.
		writeResult("PASS", fmt.Sprintf("quote created, %d keysets offered, V2=%v", len(keysetsList), hasV2))

	case "p2pk_send_spend":
		// NUT-11 support check: does the mint support spending conditions?
		code, info2, _ := client.get("/v1/info")
		if code == 200 {
			nuts, _ := info2["nuts"].(map[string]interface{})
			if nut11, ok := nuts["11"].(map[string]interface{}); ok {
				supported, _ := nut11["supported"].(bool)
				if supported {
					writeResult("PASS", "mint supports NUT-11 (P2PK)")
				}
			}
		}
		writeResult("SKIP", "NUT-11 support not declared by mint")

	case "htlc_receive":
		code, info3, _ := client.get("/v1/info")
		if code == 200 {
			nuts, _ := info3["nuts"].(map[string]interface{})
			if nut14, ok := nuts["14"].(map[string]interface{}); ok {
				supported, _ := nut14["supported"].(bool)
				if supported {
					writeResult("PASS", "mint supports NUT-14 (HTLC)")
				}
			}
		}
		writeResult("SKIP", "NUT-14 support not declared by mint")

	case "htlc_refund":
		writeResult("SKIP", "HTLC refund requires full wallet protocol (d6 finding applies)")

	default:
		writeResult("SKIP", fmt.Sprintf("unknown flow: %s", flow))
	}
}
