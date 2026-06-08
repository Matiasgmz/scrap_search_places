import os

class ProxyManager:
    """
    Gestionnaire basique de proxies pour Selenium et Requests.
    S'assure que le format est correct pour Google Chrome.
    """
    
    @staticmethod
    def format_proxy(proxy_str):
        """
        Formate une chaîne de proxy.
        Supporte IP:PORT ou http://IP:PORT.
        L'authentification (user:pass@ip:port) nécessite souvent un plugin extension pour Chrome,
        nous restons sur des proxies simples (IP authentication) pour ce module natif.
        """
        if not proxy_str:
            return None
            
        proxy_str = proxy_str.strip()
        
        # Chrome attend généralement http://IP:PORT ou IP:PORT
        if not proxy_str.startswith("http"):
            return f"http://{proxy_str}"
            
        return proxy_str

    @staticmethod
    def get_requests_proxies(proxy_str):
        """Retourne le dictionnaire de proxies pour la librairie requests (OSINT)."""
        formatted = ProxyManager.format_proxy(proxy_str)
        if not formatted:
            return None
            
        return {
            "http": formatted,
            "https": formatted
        }
