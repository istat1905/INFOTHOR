from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import time

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
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Mode sans interface
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)

    def login(self) -> bool:
        """
        Effectue la connexion au portail
        Returns:
            bool: True si connexion réussie, False sinon
        """
        try:
            print("=" * 50)
            print("DEBUT CONNEXION")
            print("=" * 50)
            
            if not self.driver:
                self._init_driver()
            
            # Étape 1: Accéder à la page d'accueil
            print("\n1. Accès page d'accueil Auchan...")
            self.driver.get(f"{self.base_url}/index.php")
            time.sleep(2)
            print(f"   URL: {self.driver.current_url}")
            
            # Étape 2: Cliquer sur "M'identifier avec mon compte @GP"
            print("\n2. Clic sur le bouton SSO @GP...")
            try:
                # Attendre et cliquer sur le bouton SSO (visible dans Image 1)
                sso_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.btn.btn-outline-red.atgp'))
                )
                sso_button.click()
                time.sleep(3)
                print(f"   ✅ Bouton SSO cliqué")
                print(f"   URL: {self.driver.current_url}")
            except Exception as e:
                print(f"   ⚠️ Bouton SSO non trouvé, tentative URL directe...")
                self.driver.get(f"{self.base_url}/call.php?call=base_sso_openid_connect_authentifier")
                time.sleep(3)
            
            # Étape 3: Remplir le formulaire de connexion (visible dans Image 2)
            print("\n3. Remplissage du formulaire de connexion...")
            
            # Attendre que la page de connexion soit chargée
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "_username"))
            )
            
            # Remplir l'email
            email_field = self.driver.find_element(By.NAME, "_username")
            email_field.clear()
            email_field.send_keys(self.username)
            print(f"   ✅ Email saisi: {self.username}")
            
            # Remplir le mot de passe
            password_field = self.driver.find_element(By.NAME, "_password")
            password_field.clear()
            password_field.send_keys(self.password)
            print(f"   ✅ Mot de passe saisi")
            
            time.sleep(1)
            
            # Étape 4: Soumettre le formulaire
            print("\n4. Soumission du formulaire...")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            submit_button.click()
            
            # Attendre la redirection
            time.sleep(5)
            print(f"   URL après soumission: {self.driver.current_url}")
            
            # Étape 5: Vérifier le succès de la connexion
            print("\n5. Vérification de la connexion...")
            
            # Vérifier qu'on est de retour sur auchan.atgpedi.net
            if 'auchan.atgpedi.net' in self.driver.current_url:
                print("   ✅ Retour sur le portail Auchan")
                
                # Vérifier les indicateurs de connexion réussie
                page_source = self.driver.page_source.lower()
                
                success_indicators = [
                    'bonjour' in page_source,
                    'commandes' in page_source,
                    'déconnexion' in page_source or 'logout' in page_source,
                    'sessionexpire' not in self.driver.current_url
                ]
                
                success_count = sum(success_indicators)
                print(f"   Indicateurs de succès: {success_count}/{len(success_indicators)}")
                
                if success_count >= 2:
                    print("\n✅ CONNEXION RÉUSSIE!")
                    print("=" * 50)
                    return True
            
            print("\n❌ CONNEXION ÉCHOUÉE")
            print("=" * 50)
            return False
            
        except Exception as e:
            print(f"\n❌ EXCEPTION: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def extract_orders(self) -> List[Dict]:
        """
        Extrait la liste des commandes
        Returns:
            List[Dict]: Liste des commandes avec leurs détails
        """
        try:
            print("\n" + "=" * 50)
            print("EXTRACTION DES COMMANDES")
            print("=" * 50)
            
            # Navigation vers la page des commandes
            orders_url = f"{self.base_url}/gui.php?query=documents_commandes_liste&page=documents_commandes_liste&acces_page=1&lines_per_page=1000"
            
            print("\n1. Navigation vers la liste des commandes...")
            self.driver.get(orders_url)
            time.sleep(3)
            print(f"   URL: {self.driver.current_url}")
            
            # Attendre que le tableau soit chargé
            print("\n2. Attente du chargement du tableau...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "tbody"))
            )
            
            # Parser la page avec BeautifulSoup
            print("\n3. Extraction des données...")
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            tbody = soup.find('tbody')
            
            if not tbody:
                print("   ❌ Tableau des commandes non trouvé")
                return []
            
            orders = []
            rows = tbody.find_all('tr')
            print(f"   Lignes trouvées: {len(rows)}")
            
            for idx, row in enumerate(rows, 1):
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
                    
                    # Vérifier que le numéro existe et est valide
                    if order['numero'] and len(order['numero']) > 3:
                        orders.append(order)
                        
                except Exception as e:
                    print(f"   ⚠️ Erreur ligne {idx}: {str(e)}")
                    continue
            
            print(f"\n✅ {len(orders)} commandes extraites avec succès!")
            print("=" * 50)
            return orders
            
        except Exception as e:
            print(f"\n❌ Erreur extraction commandes: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_text(self, cell) -> str:
        """Extrait et nettoie le texte d'une cellule"""
        if not cell:
            return ""
        text = cell.get_text(strip=True)
        return re.sub(r'\s+', ' ', text)

    def get_order_details(self, order_number: str) -> Optional[Dict]:
        """
        Récupère les détails d'une commande spécifique
        """
        try:
            detail_url = f"{self.base_url}/gui.php?page=documents_commandes_voir&numero={order_number}"
            self.driver.get(detail_url)
            time.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            details = {'numero': order_number}
            
            # Ajouter ici l'extraction des détails spécifiques
            
            return details
            
        except Exception as e:
            print(f"Erreur récupération détails: {str(e)}")
            return None

    def close(self):
        """Ferme le navigateur"""
        if self.driver:
            self.driver.quit()
            print("\n🔒 Navigateur fermé")
