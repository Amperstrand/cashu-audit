ARG GONUTS_REPO=elnosh/gonuts
FROM golang:1.22-slim AS builder
ARG GONUTS_REPO
WORKDIR /app
RUN git clone --depth=1 https://github.com/${GONUTS_REPO}.git gonuts
COPY main.go /app/driver/
WORKDIR /app/driver
RUN go mod init driver && go build -o /gonuts-driver .

FROM debian:bookworm-slim
COPY --from=builder /gonuts-driver /usr/local/bin/
ENTRYPOINT ["gonuts-driver"]
