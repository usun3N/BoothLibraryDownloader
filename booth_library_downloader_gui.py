import requests
import requests.cookies
from bs4 import BeautifulSoup
import json
from PIL import Image
import os
import configparser
import shutil
import TkEasyGUI as eg
import re

cookie_path = ""
dl_path = ""

def cookies_from_file(path: str) -> dict[str]:
    """
    path: The path to the JSON file containing the cookies.
    Load cookies from a JSON file.
    """
    cookies = requests.cookies.RequestsCookieJar()
    with open(path, "r") as f:
        for cookie in json.load(f):
            cookies.set(cookie["name"], cookie["value"])
    return cookies

class Product:
    def __init__(self, soup: BeautifulSoup, booth_user):
        urls = soup.select("a")
        self.item_url = urls[0]["href"]
        self.shop_url = urls[1]["href"]
        self.download_urls = []
        self.booth_user = booth_user
        for url in [url["href"] for url in urls[2:]]:
            if "browse" in url:
                continue
            self.download_urls.append(url)

        self.name = soup.select("div.text-text-default")[0].text
        self.name = re.sub("\\(.+?\\)", "", self.name)
        self.name = re.sub("【.+?】", "", self.name)
        self.name = re.sub("\\[.+?\\]", "", self.name)
        for char in list("/:*?\\<>| 　＆&~^%#$@"):
            self.name = self.name.replace(char, "")
        self.icon_url = soup.select("img.l-library-item-thumbnail")[0]["src"]

    def exist(self):
        return os.path.exists(f"{dl_path}\\{self.name}")
    
    def image_download(self):
        if os.path.exists(f"{dl_path}\\temp\\{self.name}.png"):
            return True
        try:
            if not os.path.exists(f"{dl_path}\\temp"):
                os.makedirs(f"{dl_path}\\temp")
            res = self.booth_user.session.get(self.icon_url)
            filename = os.path.basename(res.url.split("?")[0])
            with open(f"{dl_path}\\temp\\{filename}", "wb") as f:
                f.write(res.content)
            del res
            img = Image.open(f"{dl_path}\\temp\\{filename}")
            img.save(f"{dl_path}\\temp\\{self.name}.png", format="PNG")
            img.close()
            os.remove(f"{dl_path}\\temp\\{filename}")
            return True
        except:
            return False
        
    def ico_convert(self):
        try:
            if not os.path.exists(f"{dl_path}\\{self.name}"):
                os.makedirs(f"{dl_path}\\{self.name}")
            if not os.path.exists(f"{dl_path}\\temp\\{self.name}.png"):
                self.image_download()
            img = Image.open(f"{dl_path}\\temp\\{self.name}.png")
            img.save(f"{dl_path}\\{self.name}\\icon.ico", format="ICO")
            return True
        except:
            return False
    
    def set_desktop_ini(self):
        config = configparser.ConfigParser()
        if os.path.exists(f"{dl_path}\\{self.name}\\desktop.ini"):
            os.system(f"attrib -s -h {dl_path}\\{self.name}\\desktop.ini")
        os.system(f"attrib -r {dl_path}\\{self.name}")
        config.read(f"{dl_path}\\{self.name}\\desktop.ini")
        config[".ShellClassInfo"] = {"IconResource": "icon.ico"}
        with open(f"{dl_path}\\{self.name}\\desktop.ini", "w", encoding="utf-8") as f:
            config.write(f)
        os.system(f"attrib +s +h {dl_path}\\{self.name}\\desktop.ini")
        os.system(f"attrib +r {dl_path}\\{self.name}")

    def download_files(self):
        for url in self.download_urls:
            try:
                res = self.booth_user.session.get(url)
                name = os.path.basename(res.url.split("?")[0])
                with open(f"{dl_path}\\{self.name}\\{name}", "wb") as f:
                    f.write(res.content)
                del res
                if name.endswith(".zip"):
                    shutil.unpack_archive(f"{dl_path}\\{self.name}\\{name}", f"{dl_path}\\{self.name}")
                    os.remove(f"{dl_path}\\{self.name}\\{name}")
                print(f"Downloaded: {name}")
            except Exception as e:
                print(f"Failed to download: {e} {name}")
        else:
            return True

    def download(self):
        self.image_download()
        self.ico_convert()
        self.set_desktop_ini()
        if self.download_files():
            return True
        

class BoothUser:
    """
    cookie_path: The path to the JSON file containing the cookies.
    User class for get products, username, something on booth.
    """
    def __init__(self, cookie_path):
        self.library = "https://accounts.booth.pm/library"
        self.gifts = "https://accounts.booth.pm/library/gifts"
        self.cookie = cookies_from_file(cookie_path)
        self.session = requests.Session()
        self.session.cookies = self.cookie
        self.library_products = []
        try:
            self.username = self.get_username()
        except:
            raise Exception("Cookie is invalid")
        
    def setup(self):
        self.library_products = self.get_all_products()
    
    def download_images(self):
        for product in self.library_products:
            product.image_download()

    def convert_ico(self):
        for product in self.library_products:
            product.ico_convert()
    
    def download_all_files(self):
        for product in self.library_products:
            product.ico_convert()
            product.set_desktop_ini()
            product.download_files()

    def get_page(self, url: str) -> BeautifulSoup:
        try:
            res = self.session.get(url)
            soup = BeautifulSoup(res.text, "html.parser")
            return soup
        except:
            raise Exception("Can't get page")
    
    def get_products_from_page(self, url: str) -> list[Product]:
        products = []
        soup = self.get_page(url)
        for product_soup in soup.select("body > div.page-wrap > main > div.w-full > div.mb-16"):
            products.append(Product(product_soup, booth_user))
        return products
    
    def get_all_products(self) -> list[Product]:
        all_products = []
        last_page = self.get_last_page(self.library)
        for i in range(1, last_page + 1):
            print(f"loading page {i}/{last_page}")
            all_products += self.get_products_from_page(f"{self.library}?page={i}")
        
        last_page_gifts = self.get_last_page(self.gifts)
        for i in range(1, last_page_gifts + 1):
            print(f"loading gifts page {i}/{last_page_gifts}")
            all_products += self.get_products_from_page(f"{self.gifts}?page={i}")

        return all_products
    
    def get_last_page(self, url: str):
        soup = self.get_page(url)
        last_page = soup.select_one("a.last-page")
        if last_page is None:
            return 1
        return int(last_page["href"].split("=")[-1])
    
    def get_username(self) -> str:
        soup = self.get_page("https://booth.pm/")
        username = soup.select_one("div.user-pulldown > div.flex > span > b").text
        return username
    

booth_user = None

class ProductPage:
    def __init__(self, products: list[Product]):
        self.images = [None for _ in range(12)]
        self.products = products
        self.max_page = len(self.products) // 12
        product_list = [self.get_product_layout(product, i) for i, product in enumerate(self.products[:12])]
        self.page_layout = []
        while product_list:
            self.page_layout.append(product_list[:4])
            product_list = product_list[4:]

    def get_product_layout(self, product:Product, i:int):
        print(i)
        self.images[i] = Image.open(f"{dl_path}\\temp\\{product.name}.png")
        response = eg.Frame("", 
                            [[eg.Image(self.images[i], size=(150, 150), key=f"image_{i}")], 
                             [eg.Text(product.name, wrap_length=150, key=f"title_{i}")], 
                             [eg.Button("Download", key=f"download_{i}")]],
                             size=(150, 300))
        return response
    
    def edit(self, i: int, image_path: str, title: str, window):
        if isinstance(self.images[i], Image.Image):
            self.images[i].close()
        self.images[i] = Image.open(image_path)
        window[f"image_{i}"].update(self.images[i])
        window[f"title_{i}"].update(title)

    def change_page(self, page: int, window):
        for i, product in enumerate(self.products[page * 12: (page + 1) * 12]):
            self.edit(i, f"{dl_path}\\temp\\{product.name}.png", product.name, window)
    
    def get_page_layout(self, page: int) -> list[list]:
        return self.page_layout[page]
    
    def has_next(self, page: int) -> bool:
        return page < self.max_page
    
    def has_back(self, page: int) -> bool:
        return page > 0

        

def login_window():
    global booth_user, dl_path
    username = ""
    if os.path.exists("./booth_cookies.json"):
        cookie_path = "./booth_cookies.json"
        booth_user = BoothUser(cookie_path)
        username = booth_user.username
    layout = [[eg.Text("Booth Library Downloader", font=("Arial", 20))],
            [eg.Frame("Login information", 
                [[eg.Text("Cookie path: "),eg.Text(cookie_path,key="cookie_path")],
                [eg.Text("User Name: "),eg.Text(username, key="username")],
                [eg.Button("Select JSON file", key="cookie_path_select")]
                ])],
            [eg.Frame("", 
                [[eg.Text("Download path: "),eg.Text("Default",key="download_path")],
                [eg.Button("Select folder to download", key="download_path_select")]
                ])],
            [eg.Button("START!", disabled=True, key="start_button")]]

    login_window = eg.Window("Booth Library Downloader", layout,size=(600, 250))
    while login_window.is_alive():
        event, values = login_window.read()
        if event == "cookie_path_select":
            cookie_path = eg.popup_get_file("Select cookie path", file_types=[("JSON", "*.json")])
            if cookie_path != "":
                login_window["cookie_path"].update(cookie_path)
                booth_user = BoothUser(cookie_path)
                login_window["username"].update(booth_user.username)
                shutil.copy(cookie_path, "./booth_cookies.json")
                
                
            else:
                login_window["cookie_path"].update("")
                booth_user = None
                login_window["username"].update("")
        if event == "download_path_select":
            dl_path = eg.popup_get_folder("Select download path")
            if dl_path != "":
                login_window["download_path"].update(dl_path)
            else:
                login_window["download_path"].update("")
        if event == "start_button":
            break
        if event == eg.WIN_CLOSED:
            exit()
        if booth_user == None or dl_path == "":
            sb = True
        else:
            sb = False
        login_window["start_button"].update(disabled=sb)
    login_window.close()

def main_window():
    global booth_user
    booth_user.setup()
    booth_user.download_images()
    product_page = ProductPage(booth_user.library_products)
    page = 0
    layout = [[eg.Text("Booth Library Downloader", font=("Arial", 20))],
            [eg.Frame("Products", product_page.page_layout, key="products_key"),
             eg.Column([[eg.Button("Back", key="back", disabled=True)], [eg.Button("Next", key="next")], [eg.Button("Download All", key="download_all")]])
            ]]
    main_window = eg.Window("Booth Library Downloader", layout,size=(800, 850))
    while main_window.is_alive():
        event, values = main_window.read()
        if event == "next":
            page += 1
            for i in range(12):
                main_window[f"download_{i}"].update(disabled=False)
            product_page.change_page(page, main_window)
        if event == "back":
            page -= 1
            for i in range(12):
                main_window[f"download_{i}"].update(disabled=False)
            product_page.change_page(page, main_window)
        if event == "download_all":
            booth_user.download_all_files()
        
        if product_page.has_back(page):
            main_window["back"].update(disabled=False)
        else:
            main_window["back"].update(disabled=True)
        if product_page.has_next(page):
            main_window["next"].update(disabled=False)
        else:
            main_window["next"].update(disabled=True)
        if event.startswith("download_") and not event == "download_all":
            i = page * 12 + int(event.split("_")[1])
            main_window[event].update(disabled=True)
            product = product_page.products[i]
            product.ico_convert()
            product.set_desktop_ini()
            product.download_files()
            
        if event == eg.WIN_CLOSED:
            exit()

login_window()
main_window()