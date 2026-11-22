# Samples ("pendrive" format) as a small image, copied into the pods by an init container.
# Build from the repository root: docker build -f deploy/k8s/samples.Dockerfile -t investwatch-samples:demo .
FROM alpine:3.22
COPY samples/real /samples
RUN chmod -R a+rX /samples
USER 65534
