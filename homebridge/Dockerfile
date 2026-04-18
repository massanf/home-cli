FROM node:18-alpine

RUN npm install -g --unsafe-perm \
    homebridge \
    homebridge-http-switch \
    homebridge-web-thermostat

RUN mkdir -p /homebridge-data

COPY config.json /homebridge-data/config.json

CMD ["homebridge", "-U", "/homebridge-data"]
