from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import subprocess
from openai import OpenAI
from dotenv import load_dotenv
from .utils import get_env


class BaseScraper:
    def __init__(self, name="None") -> None:
        self.driver = self.get_chrome_driver()
        self.cookies = None

    def get_chrome_driver(self) -> Chrome:
        PROFILE = r'C:\Users\wlsgy\AppData\Local\Google\Chrome\User Data'
        PORT = 9122  # Remote debugging port number

        cmd = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
        cmd += f' --user-data-dir="{PROFILE}"'
        cmd += f' --remote-debugging-port={PORT}'
        subprocess.Popen(cmd)

        options = webdriver.ChromeOptions()
        options.add_experimental_option('debuggerAddress', f'127.0.0.1:{PORT}')  # 디버깅 포트로 연결
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-features=BlockThirdPartyCookies")
        return webdriver.Chrome(options=options)

    def login(self, login_url: str, login_button_xapth: str, input_infos: list[tuple[str, str]]) -> None:
        try:
            self.driver.get(login_url)
            time.sleep(3)

            for xpath, input_string in input_infos:
                input_element = self.driver.find_element(By.XPATH, xpath).send_keys(input_string)

            self.driver.find_element(By.XPATH, login_button_xapth).click()

            time.sleep(3)

        except NoSuchElementException as e:
            print(f"login error! no such element. {str(e)}")
            raise NoSuchElementException
        except Exception as e:
            print(f"login error! {str(e)}")
            raise e

    def driver_quit(self):
        self.driver.quit()


class Everytime_Scraper(BaseScraper):
    def __init__(self):
        super().__init__(name="eta")
        self.url_dict = {
            "home": "https://everytime.kr",
            "free_board": "https://everytime.kr/375208/p",
            "login": "https://account.everytime.kr/login",
        }

        self.xpath_dict = {
            "login__username": "/html/body/div[1]/div/form/div[1]/input[1]",
            "login__password": "/html/body/div[1]/div/form/div[1]/input[2]",
            "login__login_button": "/html/body/div[1]/div/form/input",
            "article__title": "//*[@id='container']/div[5]/article/a/h2",
            "article__content": "//*[@id='container']/div[5]/article/a/p",
            "article__comments": "//*[@id='container']/div[5]/article/div/article",
        }

    def login(self, username: str, password: str) -> bool:
        login_input_infos = [
            (self.xpath_dict["login__username"], username),
            (self.xpath_dict["login__password"], password),
        ]

        super().login(
            login_url=self.url_dict["login"],
            login_button_xapth=self.xpath_dict["login__login_button"],
            input_infos=login_input_infos,
        )

    def article_detail(self, article_url):
        self.driver.get(article_url)
        time.sleep(3)

        title, content = self._get_article_info(article_url=article_url)

        comments = self.get_comments(article_url=article_url)

        return {"title": title, "content": content, "comments": comments}

    def scrapping(self, start_page, end_page):
        articles = {}

        self.apply_cookies()

        for article_href in self._extrack_article_hrefs(start_page, end_page):
            title, content = self._get_article_info(article_url=self.url_dict['home'] + article_href)
            articles[self.url_dict["home"] + article_href] = (title, content)

        return articles.__str__()

    def _extrack_article_hrefs(self, start_page: int, end_page: int) -> list[str]:
        article_hrefs = []

        for page in range(start_page, end_page + 1):
            hrefs_in_current_page = self.get_article_hrefs_in_current_page(page)

            article_hrefs += hrefs_in_current_page

        return article_hrefs

    def get_article_hrefs_in_current_page(self, page: int) -> list[str]:
        self.driver.get(f"{self.url_dict['free_board']}/{page}")
        time.sleep(3)

        html_content = self.driver.page_source
        soup = BeautifulSoup(html_content, "html.parser")
        href_list = soup.select("article.list a.article")

        return [i.get("href") for i in href_list]

    def _get_article_info(self, article_url: str) -> tuple[str, str]:
        self.driver.get(article_url)
        time.sleep(2)

        title = self.driver.find_element(By.XPATH, self.xpath_dict["article__title"])
        content = self.driver.find_element(By.XPATH, self.xpath_dict["article__content"])
        return (title.text, content.text)

    def get_comments(self, article_url):
        self.driver.get(article_url)
        time.sleep(5)
        reply_list = []

        comments = self.driver.find_elements(By.XPATH, self.xpath_dict["article__comments"])
        for comment in comments:
            comment_class = comment.get_attribute("class")  # parent or child
            username = comment.find_element(By.TAG_NAME, "h3").text
            coment_text = comment.find_element(By.TAG_NAME, "p").text

            if comment_class == "parent":
                reply_list.append({username: coment_text, "replies": []})
            elif comment_class == "child":
                parent_reply = reply_list[-1]
                parent_reply["replies"].append({username: coment_text})
            else:
                raise KeyError("클래스명이 parent 또는 child가 아닙니다.")

        return reply_list


class GPTManager:
    def __init__(self, api_key: str, system_content: str, user_content: str = None) -> None:
        load_dotenv()
        self.__client = OpenAI(api_key=api_key)
        self.__system_content = system_content
        self.user_content = user_content

    def find_hate_article(self, articles_info) -> str:
        standard = get_env("HATE_ARTICLE_STANDARD")
        output_form = """
        ---
        href:
        제목:
        내용:
        혐오 표현 근거:
        ---
        """

        user_content = f"""
        부적절한 게시글 기준: {standard}\n
        평가할 게시글 목록: `{articles_info}`\n
        ---
        출력은 다음과 같아야 합니다.\n
        {output_form}
        """

        completion = self.__client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.__system_content},
                {"role": "user", "content": user_content},
            ],
        )
        return completion.choices[0].message.content
