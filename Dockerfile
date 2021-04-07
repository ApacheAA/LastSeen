#Python image with ML developer tools
FROM debian

#Linux utils
RUN apt update &&\
  apt install -y python3\
  python3-pip\
  tesseract-ocr\
  git\
  tmux &&\
  
#Python packages
  pip3 install --upgrade pip &&\
  pip install jupyterlab\
  scipy\
  pytesseract\
  discord