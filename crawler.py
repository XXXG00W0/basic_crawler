# A general crawler class

import selenium.common
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, UnexpectedAlertPresentException, ElementNotInteractableException, ElementClickInterceptedException
from selenium.webdriver.support.select import Select
from PIL import Image
import win32api, win32gui, win32print, win32con
from pathlib import Path
import pandas as pd
import time, json, os, random, math, urllib, requests, traceback, datetime, threading, logging
from logging.handlers import RotatingFileHandler
import urllib.request as request
import pyautogui, pyperclip, pytesseract, cv2, dominate
from dominate.tags import *
from dominate.util import raw

class MaxWaitTimeReached(Exception):
    pass

class Crawler:

    def __init__(self, cfg, webpage, stop_crawler_signal=False):
        self.stop_crawler_signal = stop_crawler_signal
        self.cfg = cfg
        self.webpage = webpage
        self.timeout = lambda t1=0.5, t2=1.0: random.uniform(t1, t2)
        if self.cfg['浏览器'].lower() == "edge":
            option = webdriver.EdgeOptions()
            option.add_argument(f"--user-data-dir={self.cfg['edge用户文件']}")
            self.driver = webdriver.Edge(options=option)
        elif self.cfg['浏览器'].lower() == "chrome":
            option = webdriver.ChromeOptions()
            option.add_argument(f"--user-data-dir={self.cfg['chrome用户文件']}")
            option.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36')
            option.add_experimental_option('excludeSwitches', ['enable-automation'])
            option.add_experimental_option('useAutomationExtension', False)
            self.driver = webdriver.Chrome(options=option)
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
        else:
            raise NotImplementedError('尚未支持其他浏览器')
        self.set_logger()
        self.make_header()
        self.start_crawler()

    def set_logger(self, logger_name='logger'):
        
        self.log_path = self.cfg['log']
        if not Path(self.log_path).exists():
            os.mkdir(self.log_path)
        today = self.get_time_string('%Y%m%d_%H%M%S')
        # 以当前项目的名字为日志名字
        proj_name = str(Path(".").absolute().stem)
        fname = str(Path(self.log_path) / Path(f'{proj_name}_log_{today}.txt'))
        self.delete_old_log(keep_n_days=7)
        print(fname)
        # 没有多线程 不打印线程名字
        if not self.stop_crawler_signal:
            fmt = '[%(asctime)s] [%(name)s] [%(levelname)s] [%(funcName)s] %(message)s'
        else:
            fmt = '[%(asctime)s] [%(name)s] [%(levelname)s] [%(threadName)s] [%(funcName)s] %(message)s'
        handler_file = RotatingFileHandler(fname, backupCount=10, encoding='utf-8')
        handler_console = logging.StreamHandler()
        handler_file.setLevel('DEBUG')
        handler_console.setLevel('DEBUG')
        formatter = logging.Formatter(fmt)
        handler_file.setFormatter(formatter)
        handler_console.setFormatter(formatter)
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel('DEBUG')
        self.logger.addHandler(handler_file)
        self.logger.addHandler(handler_console)

    def delete_old_log(self, keep_n_days=7):
        today = datetime.datetime.now()
        deadline = (today - datetime.timedelta(days=keep_n_days))
        for file in Path(self.log_path).iterdir():
            ctime = os.path.getctime(str(file))
            ctime_string = datetime.datetime.fromtimestamp(int(ctime))
            if ctime_string < deadline:
                os.remove(str(file))

    def get_week_day(self, dt: datetime.datetime):
        return dt.isoweekday()

    def start_timer(self, wait_time=30) -> threading.Timer:
        self.stop_crawler_signal = False
        timer = threading.Timer(wait_time, function=self._timer_action)
        timer.start()
        return timer
  
    def _timer_action(self):
        self.stop_crawler_signal = True
        
    def make_header(self):
        # 添加 user agent 避免被反爬虫禁止访问
        header = ('User-Agent',
                  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36')
        opener = request.build_opener()
        opener.addheaders = [header]
        request.install_opener(opener)

    def start_crawler(self):
        '''实际情况可能需覆写该函数'''
        self.driver.get(self.webpage)
        self.driver.maximize_window()
        self.panel_height = self.driver.execute_script('return window.outerHeight - window.innerHeight')

    def get_time_string(self, format="%Y-%m-%d %H:%M:%S") -> str:
        now_time = datetime.datetime.now()
        return now_time.strftime(format)
    
    def get_time_elapsed(self, t0: datetime.datetime, t1: datetime.datetime) -> str:
        '''计算两个时间的差值，以字串形式返回差值'''
        return str(abs(t0 - t1))

    def js_click_element(self, element):
        self.driver.execute_script('arguments[0].click;', element)

    def move_to_element(self, element, duration=1):
        print('[移动鼠标] 浏览器顶部状态栏高度:', self.panel_height)
        loc = element.location
        size = element.size
        click_loc_x = (loc['x'] + size['width']/2) * 1.25
        click_loc_y = (loc['y'] + size['height']/2 + self.panel_height) * 1.25
        pyautogui.moveTo(click_loc_x, click_loc_y, duration=duration)

    def click_element(self, element):
        print('[点击] 浏览器顶部状态栏高度:', self.panel_height)
        loc = element.location
        size = element.size
        click_loc_x = (loc['x'] + size['width']/2) * 1.25
        click_loc_y = (loc['y'] + size['height']/2 + self.panel_height) * 1.25
        pyautogui.click(click_loc_x, click_loc_y)

    def safe_click(self, find_by, element):
        web_object = self.wait_till_available_and_return_element(find_by, element)
        self.move_to_element(web_object, duration=self.timeout(1, 1.5))
        time.sleep(self.timeout(0.25, 0.5))
        self.click_element(web_object)

    def safe_input(self, text):
        pyautogui.hotkey('ctrl', 'a', interval=self.timeout(0.25, 0.5))
        for s in text:
            pyautogui.press(s)
            time.sleep(self.timeout(0.1, 0.15))

    def wait_alert_and_dismiss(self, timeout=-1, patience=3, err_msg='等待弹窗超时，稍后再试'):
        # 由于多次测试，网站可能保存了之前填写的信息，这时候会提示是否把保存的信息填写上去，这里选择将alert弹窗关闭   
        attempt = 1
        if timeout == -1:
            timeout = self.timeout(0, 1)
        while attempt <= patience:
            try:
                self.logger.warning(f'第{attempt}次尝试关闭弹窗')
                WebDriverWait(self.driver, timeout).until(EC.alert_is_present())
                self.driver.switch_to.alert.dismiss()
                windows = self.driver.window_handles
                self.driver.switch_to.window(windows[1])
            except selenium.common.NoAlertPresentException:
                self.logger.error(f'不存在该弹窗')
                attempt += 1
            except selenium.common.TimeoutException:
                self.logger.error(f'{err_msg}')
                attempt += 1
            else:
                return
        self.logger.debug(f'尝试次数({attempt-1})已达{patience}次')

    def wait_element_till_clickable(self, find_by, element, timeout=-1, wait_time=30, err_msg='搜索可点击元素超时，稍后再试'):
        timer: threading.Timer = self.start_timer(wait_time)
        if timeout == -1:
            timeout = self.timeout(0.25, 0.5)
        while 1:
            try:
                # time.sleep(timeout)
                WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((find_by, element)))
                self.driver.find_element(find_by, element).click()
            except selenium.common.TimeoutException:
                self.logger.error(f'{err_msg}: {element}')
            except UnexpectedAlertPresentException:
                self.wait_alert_and_dismiss()
            except ElementClickInterceptedException:
                self.logger.error(f'元素被遮挡，无法点击: {element}')
            else:
                timer.cancel()
                return
            finally:
                # 超时, 终止程序
                # print(self.stop_task, self.refresh_if_timeout)
                if self.stop_crawler_signal:
                    self.logger.error(f'超时: {element}')
                    raise MaxWaitTimeReached

    def wait_input_field_and_enter(self, find_by, element, text, clear=True, timeout=-1, wait_time=30, err_msg='搜索输入框超时，稍后再试'):
        timer: threading.Timer = self.start_timer(wait_time)
        if timeout == -1:
            timeout = self.timeout(0.25, 0.5)
        while 1:
            try:
                # time.sleep(timeout)
                WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((find_by, element)))
                input_field = self.driver.find_element(find_by, element)
                if input_field == None:
                    raise ElementNotInteractableException
                elif clear:
                    input_field.clear()
                input_field.send_keys(text)
            except ElementNotInteractableException:
                self.logger.error(f'输入框不可互动 {element}')
            except selenium.common.TimeoutException:
                self.logger.error(f'{err_msg}: {element}')
            except UnexpectedAlertPresentException:
                self.wait_alert_and_dismiss()
            else:
                timer.cancel()
                return
            finally:
                # 超时, 终止程序
                # print(self.stop_task, self.refresh_if_timeout)
                if self.stop_crawler_signal:
                    self.logger.error(f'超时: {element}')
                    raise MaxWaitTimeReached

    def wait_and_return_element(self, find_by, element, timeout=-1, err_msg='【返回元素】等待元素超时，稍后再试'):
        if timeout == -1:
            timeout = self.timeout(1, 2)
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((find_by, element)))
            return self.driver.find_element(find_by, element)
        except selenium.common.TimeoutException:
            self.logger.error(f'{err_msg}: {element}')
            return None
        except UnexpectedAlertPresentException:
            self.wait_alert_and_dismiss()
    
    def wait_and_return_element_with_patience(self, find_by, element, timeout=-1, patience=3, err_msg='【返回元素】等待元素超时，稍后再试'):
        if timeout == -1:
            timeout = self.timeout(1, 2)
        if patience <= 0:
            patience = 3
        for attempt in range(patience):
            try:
                self.logger.debug(f'第 {attempt} 次尝试 / 共 {patience} 次')
                WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((find_by, element)))
                webElement = self.driver.find_element(find_by, element)
            except selenium.common.TimeoutException:
                self.logger.error(f'{err_msg}: {element}')
            except UnexpectedAlertPresentException:
                self.wait_alert_and_dismiss()
            else:
                return webElement
    
    
    def wait_till_available_and_return_element(self, find_by, element, timeout=-1, wait_time=30, err_msg='<返回非空元素> 等待元素超时，稍后再试'):
        timer: threading.Timer = self.start_timer(wait_time)
        if timeout == -1:
            timeout = self.timeout(0.25, 0.5)
        while 1:
            try:
                # time.sleep(timeout)
                WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((find_by, element)))
                webElement = self.driver.find_element(find_by, element)
            except selenium.common.TimeoutException:
                self.logger.error(f'{err_msg}: {element}')
                print(f'[{self.get_time_string()}] {err_msg}: {element}')
            except UnexpectedAlertPresentException:
                self.wait_alert_and_dismiss()
            else:
                timer.cancel()
                return webElement
            finally:
                # 超时, 终止程序
                # print(self.stop_task, self.refresh_if_timeout)
                if self.stop_crawler_signal:
                    self.logger.error(f'超时: {element}')
                    raise MaxWaitTimeReached

    def wait_till_non_empty_element(self, find_by, element, timeout=-1, wait_time=30, err_msg='等待非空元素超时，稍后再试'):
        timer: threading.Timer = self.start_timer(wait_time)
        if timeout == -1:
            timeout = self.timeout(0.25, 0.5)
        while 1:
            try:
                # time.sleep(timeout)
                WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((find_by, element)))
                element_content = self.driver.find_element(find_by, element)
                print(element_content.text)
                if element_content != '' and element_content.text != '':
                    timer.cancel()
                    return element_content
                else:
                    self.logger.warning(f'元素为空: {element}')
            except selenium.common.TimeoutException:
                self.logger.error(f'{err_msg}: {element}')
            except UnexpectedAlertPresentException:
                self.wait_alert_and_dismiss()
            finally:
                # 超时, 终止程序
                # print(self.stop_task, self.refresh_if_timeout)
                if self.stop_crawler_signal:
                    self.logger.error(f'超时: {element}')
                    raise MaxWaitTimeReached

    def wait_and_download(self, url, path, timeout=-1, patience=3):
        if timeout == -1:
            timeout = self.timeout(1, 2)
        for attempt in range(1, patience):
            try:
                request.urlretrieve(url, path)
            except Exception as E:
                self.logger.warning(f'下载失败，第{attempt}次尝试: \n{E}')
            else:
                self.logger.debug(f'下载完成: {os.path.abspath(path)}')
                return True
        self.logger.error(f'下载失败，退出下载')
        return False
    
    def find_sub_elements(self, find_by, element, sub_element, timeout=-1, wait_time=30, err_msg="寻找子元素超时"):
        timer: threading.Timer = self.start_timer(wait_time)
        if timeout == -1:
            timeout = self.timeout(0.25, 0.5)
        while 1:
            try:
                # time.sleep(timeout)
                element_list = element.find_elements(find_by, sub_element)
            except selenium.common.TimeoutException:
                self.logger.error(f'{err_msg}:\n父元素: {element}\n子元素: {sub_element}')
            except UnexpectedAlertPresentException:
                self.wait_alert_and_dismiss()
            else:
                timer.cancel()
                return element_list
            finally:
                # 超时, 终止程序
                # print(self.stop_task, self.refresh_if_timeout)
                if self.stop_crawler_signal:
                    self.logger.error(f'超时: {element}')
                    raise MaxWaitTimeReached
    
    def randomize_tags(self, tags: list) ->str:
        '''随机打乱一级列表的标签并串联起来返回字串'''
        random.shuffle(tags)
        return " ".join(tags)
    
    def select_random_files(self, path, count=1, ext=['.jpg', '.png', '.jpeg']) -> list:
        '''随机选择<count>张图片，count默认为1，并返回图片路径列表'''
        if count <= 0:
            self.logger.warning(f'图片个数 <{count}> 不可用，已改成 <1>')
            count = 1
        image_list = self.recursive_find_files(path, ext=ext)
        return random.sample(image_list, count)
    
    def upload_file_helper(self, img):
        '''利用pyperclip、pyautogui输入图片路径并上传'''
        pyperclip.copy(str(img))
        # 避免百度每上传一个文件就弹一个已保存弹窗，导致切换窗口
        pyautogui.click(733, 678)
        pyautogui.hotkey('ctrl', 'v', interval=self.timeout(0.25, 0.5))
        pyautogui.press('enter')

    def recursive_find_files(self, root, ext) -> list:
        file_list = []
        for path in Path(root).iterdir():
            # print(path)
            # print(file_list)
            if path.is_dir():
                file_list.extend(self.recursive_find_files(path, ext=ext))
            elif path.suffix.lower() in ext:
                file_list.append(path)
                # print('file list', file_list)
        # print(file_list)
        return file_list
    
    def scroll(self, horizontal=0, vertical=200):
        self.driver.execute_script(f"window.scrollBy({horizontal},{vertical})")