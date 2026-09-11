ARG GONUTS_REPO=OpenTollGate/gonuts-tollgate
FROM golang:1.23-slim AS builder
ARG GONUTS_REPO
WORKDIR /app
RUN git clone --depth=1 https://github.com/${GONUTS_REPO}.git gonuts
COPY main.go /app/driver/
WORKDIR /app/driver
RUN go mod init driver && go build -o /gonuts-driver .

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /gonuts-driver /usr/local/bin/
ENTRYPOINT ["gonuts-driver"]
