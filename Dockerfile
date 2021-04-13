# As Scrapy runs on Python, I choose the official Python 3 Docker image.
FROM python:3

ARG elasticsearch_ip

ENV ELASTICSEARCH_IP=$elasticsearch_ip

# Set the working directory to /usr/src/app.
WORKDIR /usr/src/app

# Copy the file from the local host to the filesystem of the container at the working directory.
COPY requirements.txt ./

# Install Scrapy specified in requirements.txt.
RUN pip3 install -r requirements.txt

RUN apt-get update && apt-get -y install cron

# Copy cron file to the cron.d directory
COPY builder-cron /etc/cron.d/builder-cron

# Copy the project source code from the local host to the filesystem of the container at the working directory.
COPY scripts/* .

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/builder-cron

# Apply cron job
RUN crontab /etc/cron.d/builder-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Run the command on container startup
CMD cron && tail -f /var/log/cron.log
