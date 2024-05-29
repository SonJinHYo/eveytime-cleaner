from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from bs4.element import ResultSet
import time
from openai import OpenAI
from dotenv import load_dotenv
import os


class BaseScraper:
    def __init__(self, name="None") -> None:
        self.driver = self.get_chrome_driver()
        self.cookies = None

    def get_chrome_driver(self) -> Chrome:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-features=BlockThirdPartyCookies")

        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

        service = Service(ChromeDriverManager().install())

        return webdriver.Chrome(service=service, options=options)

    def login(
        self,
        login_url: str,
        username: str,
        password: str,
        username_xpath: str,
        password_xpath: str,
        login_button_xpath: str
    ) -> bool:
        try:
            self.driver.get(login_url)
            time.sleep(3)
            print(BeautifulSoup(self.driver.page_source, "html.parser").text)
            username_input_element = self.driver.find_element(By.XPATH, username_xpath)
            password_input_element = self.driver.find_element(By.XPATH, password_xpath)
            login_button_element = self.driver.find_element(By.XPATH, login_button_xpath)

            username_input_element.send_keys(username)
            password_input_element.send_keys(password)

            login_button_element.click()
            time.sleep(3)  # 추가적인 시간 대기
            self.cookies = self.driver.get_cookies()  # 쿠키 저장

            return True
        except NoSuchElementException as e:
            print(f"login error! no such element. {str(e)}")
            return False
        except Exception as e:
            print(f"login error! {str(e)}")
            return False

    def apply_cookies(self):
        self.driver.delete_all_cookies()  # 기존 모든 쿠키 삭제
        time.sleep(1)

        if self.cookies:
            for cookie in self.cookies:
                self.driver.add_cookie(cookie)
        else:
            print("Cookies unexist")

    def driver_quit(self):
        self.driver.quit()


class Everytime_Scraper(BaseScraper):
    def __init__(self):
        super().__init__(name="eta")

        self.__base_url = 'https://everytime.kr'
        self.__scrap_url = self.__base_url + '/375208/p/'
        self.__login_url = "https://account.everytime.kr/login"

    def login(self, username: str, password: str) -> bool:
        username_xpath = '/html/body/div[1]/div/form/div[1]/input[1]'
        password_xpath = '/html/body/div[1]/div/form/div[1]/input[2]'
        login_button_xpath = '/html/body/div[1]/div/form/input'

        try:
            self.driver.get(self.__login_url)
            time.sleep(3)
            username_input_element = self.driver.find_element(By.XPATH, username_xpath)
            password_input_element = self.driver.find_element(By.XPATH, password_xpath)
            login_button_element = self.driver.find_element(By.XPATH, login_button_xpath)

            username_input_element.send_keys(username)
            time.sleep(1)
            password_input_element.send_keys(password)
            time.sleep(1)

            login_button_element.click()
            time.sleep(5)  # 추가적인 시간 대기
            self.cookies = self.driver.get_cookies()  # 쿠키 저장
            time.sleep(1)

            return True
        except NoSuchElementException as e:
            print(f"login error! no such element. {str(e)}")
            return False
        except Exception as e:
            print(f"login error! {str(e)}")
            return False

    def scrapping(self, start_page, end_page):
        articles = {}

        self.apply_cookies()
        self.driver.refresh()
        time.sleep(1)

        for article_href in self._extrack_article_hrefs(start_page, end_page):
            title, content = self._get_article_info(article_href)
            articles[self.__base_url + article_href] = (title, content)

        return articles.__str__()

    def _extrack_article_hrefs(self, start_page: int, end_page: int) -> list[str]:
        article_hrefs = []

        for page in range(start_page, end_page + 1):
            hrefs_in_current_page = self.get_article_hrefs_in_current_page(page)

            article_hrefs += hrefs_in_current_page

        return article_hrefs

    def get_article_hrefs_in_current_page(self, page: int) -> list[str]:
        self.driver.get(f"{self.__scrap_url}{page}")
        time.sleep(3)

        html_content = self.driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        href_list = soup.select('article.list a.article')

        return [i.get('href') for i in href_list]

    def _get_article_info(self, href: str) -> tuple[str, str]:
        self.driver.get(self.__base_url + href)
        print(self.__base_url + href)
        time.sleep(1)

        title_xpath = '//*[@id="container"]/div[5]/article/a/h2'
        content_xpath = '//*[@id="container"]/div[5]/article/a/p'

        title = self.driver.find_element(By.XPATH, title_xpath)
        content = self.driver.find_element(By.XPATH, content_xpath)
        print((title.text, content.text))
        return (title.text, content.text)


class GPTManager:
    def __init__(self, api_key: str) -> None:
        load_dotenv()
        self.__client = OpenAI(api_key=api_key)
        self.__system_content = ""

    def find_hate_article(self, articles_info):
        user_content = self._get_user_content(articles_info)
        completion = self.__client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": self.__system_content
                },
                {
                    "role": "user",
                    "content": user_content
                },
            ]
        )
        return completion.choices[0].message.content

    def _get_user_content(self, articles_info):
        return f""""""


if __name__ == "__main__":
    gpt_manager = GPTManager(api_key="")
    eta_scraper = Everytime_Scraper()

    eta_scraper.login(username="", password="")
    articles_info = eta_scraper.scrapping(start_page=1, end_page=1)
    import pprint
    pprint.pprint(articles_info)
    hate_articles_info = gpt_manager.find_hate_article(articles_info=articles_info)
    pprint.pprint(hate_articles_info)

    eta_scraper.driver_quit()
