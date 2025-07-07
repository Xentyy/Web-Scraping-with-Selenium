import time
import random
import csv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import pprint

# --- CONFIGURATION ---
CONFIG = {
    "base_url": "https://www.sahibinden.com/",
    "max_listings_to_scrape": 40,  # Toplamda kaç ilan çekileceği
    "max_pages_to_scrape": 3,  # En fazla kaç sayfa gezileceği
    "output_csv_file": "sahibinden_otomobil_ilanlari_gelismis.csv",
    "wait_times": {
        "short_min": 2,
        "short_max": 5,
        "long_min": 30,  # İsteğiniz üzerine uzun bekleme süresi
        "long_max": 60,  # İsteğiniz üzerine uzun bekleme süresi
    }
}

# --- SELECTORS ---
# Sitede bir değişiklik olursa sadece bu seçicileri güncellemek yeterli
SELECTORS = {
    "cookie_accept_button": '//*[@id="onetrust-accept-btn-handler"]',
    "vasita_category": "//a[@title='Vasıta']",
    "otomobil_link": "//a[@title='Otomobil']",
    "all_listings_link": "a.all-classifieds-link",
    "results_table": "searchResultsTable",
    "listing_link_css": "tr.searchResultsItem a.classifiedTitle",
    "next_page_button": "//a[@title='Sonraki']",
    # Detay Sayfası Seçicileri
    "listing_title": "h1.classifiedDetailTitle",
    "listing_price": "div.classifiedInfo h3",
    "listing_location": "h2.classified-location",
    "info_list": "ul.classifiedInfoList li",
    "info_key": "strong",
    "info_value": "span",
    "phone_show_button": "a.show-phone-number",
    "phone_numbers_container": "ul.user-phones",
    "phone_number_span": "ul.user-phones li span:nth-of-type(2)"
}


def setup_driver():
    """Undetected Chromedriver'ı ayarlar ve başlatır."""
    print("[INFO] Tarayıcı ayarlanıyor...")
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.maximize_window()
    return driver


def human_wait(short=False):
    """Bot tespitini zorlaştırmak için insani bekleme süreleri ekler."""
    if short:
        s = random.uniform(CONFIG["wait_times"]["short_min"], CONFIG["wait_times"]["short_max"])
    else:
        s = random.uniform(CONFIG["wait_times"]["long_min"], CONFIG["wait_times"]["long_max"])
    print(f"[WAIT] {s:.1f} saniye bekleniyor...")
    time.sleep(s)


def navigate_to_listings(driver):
    """Ana sayfadan otomobil ilanları listeleme sayfasına gider."""
    print("[INFO] Sahibinden.com'a gidiliyor...")
    driver.get(CONFIG["base_url"])
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    try:
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, SELECTORS["cookie_accept_button"])))
        cookie_button.click()
        print("[SUCCESS] Çerezler kabul edildi.")
        time.sleep(1.5)
    except TimeoutException:
        print("[WARN] Çerez bildirimi bulunamadı, devam ediliyor.")

    print("[INFO] 'Vasıta' -> 'Otomobil' menüsüne gidiliyor...")
    vasita_cat = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.XPATH, SELECTORS["vasita_category"])))
    ActionChains(driver).move_to_element(vasita_cat).perform()

    otomobil_link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, SELECTORS["otomobil_link"])))
    driver.execute_script("arguments[0].click();", otomobil_link)
    print("[SUCCESS] 'Otomobil' kategorisine tıklandı.")

    human_wait(short=True)

    print("[INFO] 'Tüm İlanlar' linkine tıklanıyor...")
    all_listings_link = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, SELECTORS["all_listings_link"])))
    driver.execute_script("arguments[0].click();", all_listings_link)

    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, SELECTORS["results_table"])))
    print("[SUCCESS] İlan listeleme sayfası yüklendi.")


def get_listing_links(driver):
    """Mevcut sayfadaki tüm ilan linklerini toplar."""
    try:
        ilan_elements = driver.find_elements(By.CSS_SELECTOR, SELECTORS["listing_link_css"])
        links = [elem.get_attribute('href') for elem in ilan_elements if
                 'doping' not in elem.find_element(By.XPATH, "./..").get_attribute('class')]
        print(f"[INFO] Sayfadan {len(links)} adet (reklamsız) ilan linki bulundu.")
        return links
    except Exception as e:
        print(f"[ERROR] İlan linkleri toplanırken hata oluştu: {e}")
        return []


def scrape_listing_details(driver, url):
    """Tek bir ilanın detay sayfasından verileri çeker."""
    driver.get(url)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS["info_list"])))

    print("[INFO] Sayfa içinde rastgele kaydırma yapılıyor...")
    for _ in range(random.randint(2, 4)):
        scroll_amount = random.randint(300, 700)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.5, 1.5))

    data = {"Link": url}

    try:
        data["İlan Başlığı"] = driver.find_element(By.CSS_SELECTOR, SELECTORS["listing_title"]).text.strip()
    except NoSuchElementException:
        data["İlan Başlığı"] = "Bulunamadı"
    try:
        data["Fiyat"] = driver.find_element(By.CSS_SELECTOR, SELECTORS["listing_price"]).text.strip()
    except NoSuchElementException:
        data["Fiyat"] = "Bulunamadı"
    try:
        data["Konum"] = driver.find_element(By.CSS_SELECTOR, SELECTORS["listing_location"]).text.strip().replace('\n',
                                                                                                                 ' ')
    except NoSuchElementException:
        data["Konum"] = "Bulunamadı"


    try:
        ozellikler = driver.find_elements(By.CSS_SELECTOR, SELECTORS["info_list"])
        for ozellik in ozellikler:
            try:
                anahtar = ozellik.find_element(By.TAG_NAME, SELECTORS["info_key"]).text.strip()
                deger = ozellik.find_element(By.TAG_NAME, SELECTORS["info_value"]).text.strip()
                if anahtar:  # Boş anahtarları alma
                    data[anahtar] = deger
            except NoSuchElementException:
                continue
    except Exception as e:
        print(f"[WARN] Detaylı özellikler çekilirken bir sorun oluştu: {e}")


    try:
        phone_button = driver.find_element(By.CSS_SELECTOR, SELECTORS["phone_show_button"])
        driver.execute_script("arguments[0].click();", phone_button)

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, SELECTORS["phone_number_span"]))
        )

        phone_elements = driver.find_element(By.CSS_SELECTOR, SELECTORS["phone_numbers_container"]).find_elements(
            By.TAG_NAME, "li")
        phone_list = [p.text.strip().replace('\n', ' ') for p in phone_elements if p.text.strip()]
        data['Cep Telefonu'] = ", ".join(phone_list) if phone_list else "Bulunamadı"
        print(f"[SUCCESS] Telefon numarası başarıyla çekildi: {data['Cep Telefonu']}")
    except (NoSuchElementException, TimeoutException):
        data['Cep Telefonu'] = "Bulunamadı veya gizli"
        print("[WARN] Telefon numarası bulunamadı veya gizli.")
    except Exception as e:
        data['Cep Telefonu'] = "Çekerken hata oluştu"
        print(f"[ERROR] Telefon numarası çekilirken beklenmedik bir hata: {e}")

    return data


def save_to_csv(data_list, filename):
    """Toplanan verileri bir CSV dosyasına kaydeder."""
    if not data_list:
        print("[WARN] Kaydedilecek veri bulunamadı.")
        return

    print(f"\n[INFO] Toplam {len(data_list)} ilan verisi '{filename}' dosyasına kaydediliyor...")

    all_keys = set()
    for item in data_list:
        all_keys.update(item.keys())


    fieldnames = sorted(list(all_keys))

    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data_list)
        print(f"[SUCCESS] Veriler başarıyla '{filename}' dosyasına kaydedildi.")
    except Exception as e:
        print(f"[FATAL] CSV dosyasına yazma sırasında kritik bir hata oluştu: {e}")


def main():
    """Ana program akışı."""
    driver = setup_driver()
    all_scraped_data = []

    try:
        navigate_to_listings(driver)

        page_count = 1
        while page_count <= CONFIG["max_pages_to_scrape"]:
            print(f"\n--- Sayfa {page_count} işleniyor ---")

            links_on_page = get_listing_links(driver)
            if not links_on_page:
                print("[WARN] Bu sayfada işlenecek link bulunamadı. Sonraki sayfaya geçiliyor.")
                break

            for i, link in enumerate(links_on_page):
                if len(all_scraped_data) >= CONFIG["max_listings_to_scrape"]:
                    print(
                        f"[INFO] Belirlenen maksimum ilan sayısına ({CONFIG['max_listings_to_scrape']}) ulaşıldı. İşlem durduruluyor.")
                    break

                print(f"\n-> İlan {len(all_scraped_data) + 1}/{CONFIG['max_listings_to_scrape']} çekiliyor...")
                human_wait()

                try:
                    ilan_verisi = scrape_listing_details(driver, link)
                    all_scraped_data.append(ilan_verisi)
                    print(f"[SUCCESS] İlan verisi çekildi: {ilan_verisi.get('İlan Başlığı', 'Başlıksız')}")

                except Exception as e:
                    print(f"[ERROR] İlan {link} işlenirken bir hata oluştu, atlanıyor: {e}")
                    continue

            if len(all_scraped_data) >= CONFIG["max_listings_to_scrape"]:
                break

            # Sonraki sayfa
            try:
                print("\n[INFO] Sonraki sayfaya geçiliyor...")
                next_page = driver.find_element(By.XPATH, SELECTORS["next_page_button"])
                driver.execute_script("arguments[0].scrollIntoView(true);", next_page)
                time.sleep(1)
                next_page.click()
                WebDriverWait(driver, 20).until(EC.staleness_of(next_page))  # Eski butonun kaybolmasını bekle
                page_count += 1
            except (NoSuchElementException, TimeoutException):
                print("[INFO] Son sayfaya ulaşıldı. Başka sayfa yok.")
                break  # Sonraki sayfa butonu yoksa döngüden çık

    finally:
        print("\n--- İŞLEM TAMAMLANDI ---")
        if all_scraped_data:
            print(f"Toplam {len(all_scraped_data)} adet ilan verisi başarıyla çekildi.")
            print("\nÖrnek Veri:")
            pprint.pprint(all_scraped_data[0])
            save_to_csv(all_scraped_data, CONFIG["output_csv_file"])
        else:
            print("Hiçbir ilan verisi çekilemedi.")

        input("\nTarayıcıyı kapatmak için Enter'a basın...")
        if driver:
            driver.quit()
            print("[INFO] Tarayıcı kapatıldı.")


if __name__ == "__main__":
    main()