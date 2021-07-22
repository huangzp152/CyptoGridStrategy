# -*- coding: utf-8 -*-

import os
import sys
import re
import logging.handlers
from logging.handlers import TimedRotatingFileHandler

from log.utils import FileUtils

BaseDir=os.path.dirname(__file__)
sys.path.append(os.path.join(BaseDir,'../..'))

logger = logging.getLogger('galaperf')
logger.setLevel(logging.DEBUG)
fmt = logging.Formatter('[%(asctime)s]%(levelname)s:%(name)s:%(module)s:%(message)s')
streamhandler=logging.StreamHandler(sys.stdout)
streamhandler.setFormatter(fmt)
# 调试时改为DEBUG 发布改为 INFO
streamhandler.setLevel(logging.INFO)
dir = os.path.join(FileUtils.get_top_dir(), 'logs')
FileUtils.makedir(dir)
log_file = os.path.join(dir,"mobileperf_log")
log_file_handler = TimedRotatingFileHandler(filename=log_file, when="D", interval=1, backupCount=3)
log_file_handler.suffix = "%Y-%m-%d_%H-%M-%S.log"
log_file_handler.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}.log$")
log_file_handler.setFormatter(fmt)
log_file_handler.setLevel(logging.DEBUG)

logger.addHandler(streamhandler)
logger.addHandler(log_file_handler)

if __name__=="__main__":
	logger.debug("测试3！")