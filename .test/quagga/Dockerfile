FROM        alpine:latest
RUN         apk add quagga supervisor
VOLUME      /etc/quagga
EXPOSE      179 2601 2604 2605
# Supervisord
ADD         supervisord.conf /etc/supervisord.conf
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
