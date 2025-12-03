import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import time

class AuchanScraper:
    """
    Scraper pour extraire les commandes du portail Auchan
    """
    
    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password
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
    
    def login(self) -> bool:
        """
        Effectue la connexion au portail
        Returns:
            bool: True si connexion réussie, False sinon
        """
        try:
            # Étape 1: Accéder à la page d'accueil
            response = self.session.get(f"{self.base_url}/index.php")
            if response.status_code != 200:
                print(f"Erreur lors de l'accès à la page d'accueil: {response.status_code}")
                return False
            
            # Étape 2: Cliquer sur le bouton de connexion SSO
            # Simuler le clic sur call.php?call=base_sso_openid_connect_authentifier
            auth_url = f"{self.base_url}/call.php?call=base_sso_openid_connect_authentifier"
            response = self.session.get(auth_url, allow_redirects=True)
            
            if response.status_code != 200:
                print(f"Erreur lors de la redirection SSO: {response.status_code}")
                return False
            
            # Étape 3: Récupérer la page de connexion @GP
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Trouver le formulaire de connexion
            form = soup.find('form')
            if not form:
                print("Formulaire de connexion non trouvé")
                return False
            
            # Extraire l'URL d'action du formulaire
            form_action = form.get('action', '')
            if not form_action.startswith('http'):
                form_action = f"https://www.atgp.net{form_action}"
            
            # Préparer les données de connexion
            login_data = {
                'username': self.login,
                'password': self.password
            }
            
            # Ajouter tous les champs cachés du formulaire
            for input_field in form.find_all('input', type='hidden'):
                name = input_field.get('name')
                value = input_field.get('value', '')
                if name:
                    login_data[name] = value
            
            # Étape 4: Soumettre le formulaire de connexion
            response = self.session.post(form_action, data=login_data, allow_redirects=True)
            
            if response.status_code != 200:
                print(f"Erreur lors de la soumission du formulaire: {response.status_code}")
                return False
            
            # Vérifier si la connexion a réussi
            # On vérifie la présence d'éléments typiques d'une session connectée
            if "Bonjour" in response.text or "TUGBA AKMAN" in response.text or "Commandes" in response.text:
                print("Connexion réussie!")
                return True
            else:
                print("La connexion a échoué - identifiants incorrects ou processus modifié")
                return False
            
        except Exception as e:
            print(f"Erreur lors de la connexion: {str(e)}")
            return False
    
    def extract_orders(self) -> List[Dict]:
        """
        Extrait la liste des commandes
        Returns:
            List[Dict]: Liste des commandes avec leurs détails
        """
        try:
            # Accéder à la page de la liste des commandes
            orders_url = f"{self.base_url}/gui.php?page=documents_commandes_liste"
            
            # D'abord, effacer les filtres si présents
            clear_filters_url = f"{self.base_url}/gui.php?query=documents_commandes_liste&page=documents_commandes_liste&acces_page=1&lines_per_page=100"
            response = self.session.get(clear_filters_url)
            
            time.sleep(1)  # Petite pause pour laisser le serveur traiter
            
            # Récupérer toutes les commandes (100 par page)
            response = self.session.get(orders_url + "&lines_per_page=1000")
            
            if response.status_code != 200:
                print(f"Erreur lors de l'accès à la liste des commandes: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Trouver le tableau des commandes
            # Le tableau est dans un <tbody> avec des lignes <tr>
            tbody = soup.find('tbody')
            if not tbody:
                print("Tableau des commandes non trouvé")
                return []
            
            orders = []
            rows = tbody.find_all('tr')
            
            print(f"Nombre de lignes trouvées: {len(rows)}")
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 8:  # Vérifier qu'il y a suffisamment de colonnes
                        continue
                    
                    # Extraire les données de chaque colonne
                    # Basé sur la structure visible dans l'image
                    order = {
                        'numero': self._extract_text(cells[1]),  # Numéro
                        'client': self._extract_text(cells[2]),  # Client (Auchan France)
                        'livrer_a': self._extract_text(cells[3]),  # Livrer à (PFI...)
                        'creation_le': self._extract_text(cells[4]),  # Date de création
                        'livrer_le': self._extract_text(cells[5]),  # Date de livraison
                        'gln_commande_par': self._extract_text(cells[6]),  # GLN
                        'montant_calcule': self._extract_text(cells[7]),  # Montant
                        'statut': self._extract_text(cells[8]) if len(cells) > 8 else '',  # Statut
                    }
                    
                    # Ne garder que les commandes avec un numéro valide
                    if order['numero'] and len(order['numero']) > 3:
                        orders.append(order)
                
                except Exception as e:
                    print(f"Erreur lors de l'extraction d'une ligne: {str(e)}")
                    continue
            
            print(f"Nombre de commandes extraites: {len(orders)}")
            return orders
            
        except Exception as e:
            print(f"Erreur lors de l'extraction des commandes: {str(e)}")
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
    
    def get_order_details(self, order_number: str) -> Optional[Dict]:
        """
        Récupère les détails d'une commande spécifique
        Args:
            order_number: Numéro de la commande
        Returns:
            Dict: Détails de la commande
        """
        try:
            # URL pour voir les détails d'une commande
            # À adapter selon la structure réelle du site
            detail_url = f"{self.base_url}/gui.php?page=documents_commandes_voir&numero={order_number}"
            response = self.session.get(detail_url)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraction des détails (à personnaliser selon vos besoins)
            details = {
                'numero': order_number,
                # Ajouter d'autres champs selon la structure de la page
            }
            
            return details
            
        except Exception as e:
            print(f"Erreur lors de la récupération des détails: {str(e)}")
            return None
    
    def close(self):
        """
        Ferme la session
        """
        self.session.close()


# Exemple d'utilisation
if __name__ == "__main__":
    # Test du scraper
    login = "bakfrance@baktat.com"
    password = "votre_mot_de_passe"
    
    scraper = AuchanScraper(login, password)
    
    print("Tentative de connexion...")
    if scraper.login():
        print("Connexion réussie!")
        
        print("\nExtraction des commandes...")
        orders = scraper.extract_orders()
        
        print(f"\nNombre de commandes trouvées: {len(orders)}")
        
        if orders:
            print("\nPremière commande:")
            for key, value in orders[0].items():
                print(f"  {key}: {value}")
    else:
        print("Échec de la connexion")
    
    scraper.close()
