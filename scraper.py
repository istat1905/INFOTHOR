import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional, Callable
import time

class AuchanScraper:
    """
    Scraper intelligent pour extraire les commandes du portail Auchan
    Avec détection de session et rapport d'étapes détaillé
    """
    
    def __init__(self, login: str, password: str, progress_callback: Optional[Callable] = None):
        self.username = login
        self.user_password = password
        self.base_url = "https://auchan.atgpedi.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        # Augmenter les timeouts
        self.timeout = 30  # 30 secondes au lieu de 10
        self.progress_callback = progress_callback
        self.steps_log = []
    
    def log_step(self, step: str, status: str = "info", details: str = ""):
        """
        Enregistre une étape du processus
        Args:
            step: Nom de l'étape
            status: success, error, warning, info
            details: Détails supplémentaires
        """
        log_entry = {
            'step': step,
            'status': status,
            'details': details,
            'timestamp': time.time()
        }
        self.steps_log.append(log_entry)
        
        if self.progress_callback:
            self.progress_callback(log_entry)
    
    def check_if_logged_in(self) -> bool:
        """
        Vérifie si une session est déjà active
        Returns:
            bool: True si déjà connecté, False sinon
        """
        try:
            self.log_step("🔍 Vérification session existante", "info")
            response = self.session.get(f"{self.base_url}/gui.php?page=accueil", timeout=self.timeout)
            
            if response.status_code != 200:
                self.log_step("⚠️ Page accueil inaccessible", "warning", f"Status: {response.status_code}")
                return False
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Vérifier la présence d'éléments typiques d'une session connectée
            is_logged = (
                "Bonjour" in response.text or 
                "TUGBA AKMAN" in response.text or
                soup.find('a', href=re.compile(r'documents_commandes')) is not None
            )
            
            if is_logged:
                self.log_step("✅ Session déjà active", "success", "Pas besoin de se reconnecter")
                return True
            else:
                self.log_step("ℹ️ Aucune session active", "info", "Connexion nécessaire")
                return False
                
        except Exception as e:
            self.log_step("❌ Erreur vérification session", "error", str(e))
            return False
    
    def find_commandes_button(self) -> Optional[str]:
        """
        Cherche le bouton/lien "Commandes" dans la page
        Returns:
            str: URL du lien commandes ou None
        """
        try:
            self.log_step("🔎 Recherche du bouton Commandes", "info")
            response = self.session.get(f"{self.base_url}/gui.php?page=accueil", timeout=10)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Chercher le lien commandes
            commandes_link = soup.find('a', href=re.compile(r'documents_commandes_liste'))
            
            if commandes_link:
                href = commandes_link.get('href', '')
                if href.startswith('gui.php'):
                    full_url = f"{self.base_url}/{href}"
                else:
                    full_url = href
                
                self.log_step("✅ Bouton Commandes trouvé", "success", f"URL: {href}")
                return full_url
            else:
                self.log_step("⚠️ Bouton Commandes non trouvé", "warning")
                return None
                
        except Exception as e:
            self.log_step("❌ Erreur recherche bouton", "error", str(e))
            return None
    
    def clear_filters(self) -> bool:
        """
        Efface les filtres en cliquant sur la gomme (icône fa-eraser)
        Returns:
            bool: True si filtres effacés, False sinon
        """
        try:
            self.log_step("🧹 Recherche de filtres actifs", "info")
            
            # Accéder à la page des commandes
            orders_url = f"{self.base_url}/gui.php?page=documents_commandes_liste"
            response = self.session.get(orders_url, timeout=10)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Chercher l'icône gomme (fa-eraser)
            eraser_icon = soup.find('i', class_=re.compile(r'fa-eraser'))
            
            if eraser_icon:
                # Trouver le lien parent
                clear_link = eraser_icon.find_parent('a')
                
                if clear_link and clear_link.get('href'):
                    self.log_step("🗑️ Filtres détectés, effacement...", "info")
                    
                    href = clear_link.get('href')
                    if href.startswith('gui.php'):
                        clear_url = f"{self.base_url}/{href}"
                    else:
                        clear_url = href
                    
                    # Cliquer sur le lien pour effacer les filtres
                    response = self.session.get(clear_url, timeout=10)
                    
                    if response.status_code == 200:
                        self.log_step("✅ Filtres effacés", "success")
                        time.sleep(0.5)  # Petite pause pour laisser le serveur traiter
                        return True
                    else:
                        self.log_step("⚠️ Échec effacement filtres", "warning", f"Status: {response.status_code}")
                        return False
                else:
                    self.log_step("⚠️ Lien gomme introuvable", "warning")
                    return False
            else:
                self.log_step("ℹ️ Aucun filtre actif", "info", "Pas besoin d'effacer")
                return True
                
        except Exception as e:
            self.log_step("❌ Erreur effacement filtres", "error", str(e))
            return False
    
    def perform_login(self) -> bool:
        """
        Effectue la connexion complète au portail
        Returns:
            bool: True si connexion réussie, False sinon
        """
        try:
            # Étape 1: Accéder à la page d'accueil
            self.log_step("🌐 Accès page d'accueil", "info")
            response = self.session.get(f"{self.base_url}/index.php", timeout=10)
            
            if response.status_code != 200:
                self.log_step("❌ Page d'accueil inaccessible", "error", f"Status: {response.status_code}")
                return False
            
            self.log_step("✅ Page d'accueil accessible", "success")
            
            # Étape 2: Cliquer sur le bouton de connexion SSO
            self.log_step("🔐 Initialisation SSO", "info")
            auth_url = f"{self.base_url}/call.php?call=base_sso_openid_connect_authentifier"
            response = self.session.get(auth_url, allow_redirects=True, timeout=10)
            
            if response.status_code != 200:
                self.log_step("❌ Redirection SSO échouée", "error", f"Status: {response.status_code}")
                return False
            
            self.log_step("✅ Redirection SSO réussie", "success")
            
            # Étape 3: Récupérer la page de connexion @GP
            self.log_step("📝 Analyse formulaire connexion", "info")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Trouver le formulaire de connexion
            form = soup.find('form')
            if not form:
                self.log_step("❌ Formulaire de connexion non trouvé", "error")
                return False
            
            self.log_step("✅ Formulaire trouvé", "success")
            
            # Extraire l'URL d'action du formulaire
            form_action = form.get('action', '')
            if not form_action.startswith('http'):
                form_action = f"https://www.atgp.net{form_action}"
            
            # Préparer les données de connexion
            login_data = {
                'username': self.username,
                'password': self.user_password
            }
            
            # Ajouter tous les champs cachés du formulaire
            for input_field in form.find_all('input', type='hidden'):
                name = input_field.get('name')
                value = input_field.get('value', '')
                if name:
                    login_data[name] = value
            
            self.log_step(f"📤 Soumission identifiants ({self.username})", "info")
            
            # Étape 4: Soumettre le formulaire de connexion
            response = self.session.post(form_action, data=login_data, allow_redirects=True, timeout=15)
            
            if response.status_code != 200:
                self.log_step("❌ Soumission formulaire échouée", "error", f"Status: {response.status_code}")
                return False
            
            # Vérifier si la connexion a réussi
            if "Bonjour" in response.text or "TUGBA AKMAN" in response.text or "Commandes" in response.text:
                self.log_step("✅ Connexion réussie", "success", "Session établie")
                return True
            else:
                self.log_step("❌ Connexion échouée", "error", "Identifiants incorrects ou processus modifié")
                return False
            
        except requests.Timeout:
            self.log_step("❌ Timeout de connexion", "error", "Le serveur met trop de temps à répondre")
            return False
        except Exception as e:
            self.log_step("❌ Erreur connexion", "error", str(e))
            return False
    
    def login(self) -> bool:
        """
        Processus de connexion intelligent avec détection de session et mode secours
        Returns:
            bool: True si connecté (ou déjà connecté), False sinon
        """
        self.log_step("🚀 Début du processus de connexion", "info")
        
        # Vérifier si déjà connecté
        if self.check_if_logged_in():
            return True
        
        # Sinon, effectuer la connexion
        login_success = self.perform_login()
        
        # Mode secours : si échec, tester accès direct à la page commandes
        if not login_success:
            self.log_step("🔄 Mode secours activé", "warning", "Test accès direct page commandes")
            return self.test_direct_access()
        
        return login_success
    
    def test_direct_access(self) -> bool:
        """
        Mode secours : teste l'accès direct à la page des commandes
        Utile si la session est déjà active mais le processus de login a échoué
        Returns:
            bool: True si accès possible, False sinon
        """
        try:
            self.log_step("🎯 Test accès direct page commandes", "info")
            
            orders_url = f"{self.base_url}/gui.php?page=documents_commandes_liste"
            response = self.session.get(orders_url, timeout=10)
            
            if response.status_code != 200:
                self.log_step("❌ Accès direct impossible", "error", f"Status: {response.status_code}")
                return False
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Vérifier si on est bien sur la page des commandes (présence du tableau)
            tbody = soup.find('tbody')
            has_table = tbody is not None
            
            # Vérifier qu'on n'est pas redirigé vers la page de login
            has_login_form = soup.find('input', {'type': 'password'}) is not None
            
            if has_table and not has_login_form:
                self.log_step("✅ Accès direct réussi !", "success", "Session valide détectée")
                return True
            elif has_login_form:
                self.log_step("❌ Redirection vers login", "error", "Session expirée, identifiants requis")
                return False
            else:
                self.log_step("⚠️ Page inattendue", "warning", "Structure HTML différente")
                return False
                
        except requests.Timeout:
            self.log_step("❌ Timeout accès direct", "error", "Le serveur ne répond pas")
            return False
        except Exception as e:
            self.log_step("❌ Erreur accès direct", "error", str(e))
            return False
    
    def extract_orders(self) -> List[Dict]:
        """
        Extrait la liste des commandes avec effacement automatique des filtres
        Returns:
            List[Dict]: Liste des commandes avec leurs détails
        """
        try:
            self.log_step("📋 Début extraction commandes", "info")
            
            # Étape 1: S'assurer qu'on est sur la bonne page
            orders_url = f"{self.base_url}/gui.php?page=documents_commandes_liste"
            
            self.log_step("🌐 Accès page commandes", "info")
            response = self.session.get(orders_url, timeout=10)
            
            if response.status_code != 200:
                self.log_step("❌ Page commandes inaccessible", "error", f"Status: {response.status_code}")
                return []
            
            self.log_step("✅ Page commandes accessible", "success")
            
            # Étape 2: Effacer les filtres si présents
            self.clear_filters()
            
            # Étape 3: Récupérer toutes les commandes (augmenter le nombre par page)
            self.log_step("📥 Récupération données (max 1000)", "info")
            response = self.session.get(orders_url + "&lines_per_page=1000", timeout=15)
            
            if response.status_code != 200:
                self.log_step("❌ Échec récupération données", "error", f"Status: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Trouver le tableau des commandes
            self.log_step("🔍 Analyse du tableau", "info")
            tbody = soup.find('tbody')
            
            if not tbody:
                self.log_step("⚠️ Tableau non trouvé", "warning", "Structure HTML peut-être différente")
                return []
            
            orders = []
            rows = tbody.find_all('tr')
            
            self.log_step(f"📊 {len(rows)} lignes détectées", "info")
            
            for idx, row in enumerate(rows):
                try:
                    cells = row.find_all('td')
                    if len(cells) < 8:  # Vérifier qu'il y a suffisamment de colonnes
                        continue
                    
                    # Extraire les données de chaque colonne
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
                    
                    # Ne garder que les commandes avec un numéro valide
                    if order['numero'] and len(order['numero']) > 3:
                        orders.append(order)
                
                except Exception as e:
                    self.log_step(f"⚠️ Erreur ligne {idx+1}", "warning", str(e))
                    continue
            
            if len(orders) > 0:
                self.log_step(f"✅ Extraction terminée", "success", f"{len(orders)} commandes extraites")
            else:
                self.log_step("⚠️ Aucune commande extraite", "warning", "Vérifier la structure du tableau")
            
            return orders
            
        except requests.Timeout:
            self.log_step("❌ Timeout extraction", "error", "Le serveur met trop de temps à répondre")
            return []
        except Exception as e:
            self.log_step("❌ Erreur extraction", "error", str(e))
            return []
    
    def _extract_text(self, cell) -> str:
        """
        Extrait et nettoie le texte d'une cellule
        Args:
            cell: Élément BeautifulSoup de la cellule
        Returns:
            str: Texte nettoyé
        """
        if not cell:
            return ""
        
        # Récupérer tout le texte et nettoyer
        text = cell.get_text(strip=True)
        
        # Nettoyer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def get_steps_log(self) -> List[Dict]:
        """
        Retourne le log complet des étapes
        Returns:
            List[Dict]: Liste des étapes avec statut
        """
        return self.steps_log
    
    def close(self):
        """
        Ferme la session
        """
        self.log_step("🔚 Fermeture session", "info")
        self.session.close()


# Exemple d'utilisation avec callback
if __name__ == "__main__":
    def print_progress(log_entry):
        status_icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        icon = status_icons.get(log_entry['status'], '•')
        print(f"{icon} {log_entry['step']}")
        if log_entry['details']:
            print(f"   → {log_entry['details']}")
    
    login = "bakfrance@baktat.com"
    password = "votre_mot_de_passe"
    
    scraper = AuchanScraper(login, password, progress_callback=print_progress)
    
    if scraper.login():
        orders = scraper.extract_orders()
        print(f"\n🎉 {len(orders)} commandes récupérées")
    
    scraper.close()
