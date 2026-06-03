FROM python:3.12-slim
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY . /code
# Run as an unprivileged user so a download cannot write to the container as root.
RUN useradd --create-home appuser \
    && mkdir -p /code/data \
    && chown -R appuser:appuser /code/data
USER appuser
ENTRYPOINT ["python", "downloader.py"]
