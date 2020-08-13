FROM continuumio/miniconda3:latest

RUN apt-get update
RUN apt-get -y install gcc

ADD environment.yml /opt/spri_explore/environment.yml
RUN conda env create -f /opt/spri_explore/environment.yml -p /opt/conda/envs/film

COPY ./ /opt/spri_explore/
WORKDIR /opt/spri_explore

RUN echo "source activate film" > ~/.bashrc
ENV PATH /opt/conda/envs/film/bin:$PATH
ENV CONDA_DEFAULT_ENV film

CMD gunicorn --bind 0.0.0.0:$PORT wsgi:app
#CMD python wsgi.py