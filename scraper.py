from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import time
import os

class AuchanScraper:
    """
    Scraper pour extraire les commandes du portail Auchan avec Selenium
    """

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.base_url = "https://auchan.atgpedi.net"
        self.driver = None
        
    def _init_driver(self):
        """Initialise le driver Chrome avec les bonnes options"""
        print("🔧 Initialisation du navigateur...")
        
        chrome_options = Options()
        
        # Options pour Streamlit Cloud
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Désactiver les logs verbeux
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        chrome_options.add_argument('--log-level=3')
        
        try:
            # Utiliser webdriver-manager pour gérer Chrome automatiquement
            service = Service(
                ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
            )
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            print("✅ Navigateur initialisé")
            
        except Exception as e:
            print(f"❌ Erreur initialisation navigateur: {e}")
            raise

    def login(self) -> bool:
        """
        Effectue la connexion au portail
        Returns:
            bool: True si connexion réussie, False sinon
        """
        try:
            print("\n" + "=" * 50)
            print("DEBUT CONNEXION")
            print("=" * 50)
            
            if not self.driver:
                self._init_driver()
            
            # Étape 1: Accéder à la page d'accueil
            print("\n1. Accès page d'accueil...")
            self.driver.get(f"{self.base_url}/index.php")
            time.sleep(2)
            print(f"   ✅ Page chargée")
            
            # Étape 2: Cliquer sur le bouton SSO
            print("\n2. Clic sur le bouton SSO...")
            try:
                sso_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.btn.btn-outline-red.atgp, a[href*="sso"]'))
                )
                sso_button.click()
                time.sleep(3)
                print(f"   ✅ Redirection SSO")
            except:
                print(f"   ⚠️ Tentative URL directe...")
                self.driver.get(f"{self.base_url}/call.php?call=base_sso_openid_connect_authentifier")
                time.sleep(3)
            
            # Étape 3: Remplir le formulaire
            print("\n3. Remplissage formulaire...")
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "_username"))
            )
            
            email_field = self.driver.find_element(By.NAME, "_username")
            email_field.clear()
            email_field.send_keys(self.username)
            print(f"   ✅ Email: {self.username}")
            
            password_field = self.driver.find_element(By.NAME, "_password")
            password_field.clear()
            password_field.send_keys(self.password)
            print(f"   ✅ Mot de passe saisi")
            
            time.sleep(1)
            
            # Étape 4: Soumettre
            print("\n4. Soumission...")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            submit_button.click()
            
            time.sleep(5)
            
            # Étape 5: Vérification
            print("\n5. Vérification...")
            
            if 'auchan.atgpedi.net' in self.driver.current_url:
                page_source = self.driver.page_source.lower()
                
                if any(word in page_source for word in ['bonjour', 'commandes', 'déconnexion']):
                    print("\n✅ CONNEXION RÉUSSIE!")
                    print("=" * 50)
                    return True
            
            print("\n❌ CONNEXION ÉCHOUÉE")
            print("=" * 50)
            return False
            
        except Exception as e:
            print(f"\n❌ EXCEPTION: {str(e)}")
            return False

    def extract_orders(self) -> List[Dict]:
        """
        Extrait la liste des commandes
        """
        try:
            print("\n" + "=" * 50)
            print("EXTRACTION DES COMMANDES")
            print("=" * 50)
            
            orders_url = f"{self.base_url}/gui.php?query=documents_commandes_liste&page=documents_commandes_liste&acces_page=1&lines_per_page=1000"
            
            print("\n1. Navigation...")
            self.driver.get(orders_url)
            time.sleep(3)
            
            print("\n2. Attente tableau...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "tbody"))
            )
            
            print("\n3. Extraction données...")
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            tbody = soup.find('tbody')
            
            if not tbody:
                print("   ❌ Tableau non trouvé")
                return []
            
            orders = []
            rows = tbody.find_all('tr')
            print(f"   Lignes trouvées: {len(rows)}")
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 8:
                        continue
                    
                    order = {
                        'numero': self._extract_text(cells[1]),
                        'client': self._extract_text(cells[2]),
                        'livrer_a': self._extract_text(cells[3]),
                        'creation_le': self._extract_text(cells[4]),
                        'livrer_le': self._extract_text(cells[5]),
                        'gln_commande_par': self._extract_text(cells[6]),
                        'montant_calcule': self._extract_text(cells[7]),
                        'statut': self._extract_text(cells[8]) if len(cells) > 8 else '',
                    }
                    
                    if order['numero'] and len(order['numero']) > 3:
                        orders.append(order)
                        
                except Exception as e:
                    continue
            
            print(f"\n✅ {len(orders)} commandes extraites!")
            print("=" * 50)
            return orders
            
        except Exception as e:
            print(f"\n❌ Erreur: {str(e)}")
            return []

    def _extract_text(self, cell) -> str:
        if not cell:
            return ""
        text = cell.get_text(strip=True)
        return re.sub(r'\s+', ' ', text)

    def get_order_details(self, order_number: str) -> Optional[Dict]:
        try:
            detail_url = f"{self.base_url}/gui.php?page=documents_commandes_voir&numero={order_number}"
            self.driver.get(detail_url)
            time.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            details = {'numero': order_number}
            
            return details
            
        except Exception as e:
            print(f"Erreur détails: {str(e)}")
            return None

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
                print("\n🔒 Navigateur fermé")
            except:
                pass
