FROM golang:1.22-slim AS builder
ARG GONUTS_VARIANT=Origami74/gonuts-tollgate
WORKDIR /app
RUN git clone --depth=1 https://github.com/${GONUTS_VARIANT}.git gonuts
WORKDIR /app/driver
COPY main.go .
RUN go mod init driver && go mod edit -replace gonuts=/app/gonuts && go mod tidy && go build -o /gonuts-driver .

FROM debian:bookworm-slim
COPY --from=builder /gonuts-driver /usr/local/bin/
ENTRYPOINT ["gonuts-driver"]
