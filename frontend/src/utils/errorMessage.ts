// Axe 6 — traduction des erreurs réseau/axios en messages clairs en français.

export function friendlyNetworkError(error: any): string {
  // Timeout axios
  if (error?.code === "ECONNABORTED" || /timeout/i.test(error?.message || "")) {
    return "Le serveur met trop de temps à répondre. Il est peut-être en cours de redémarrage — réessaie dans quelques secondes.";
  }

  // Pas de réponse du serveur (backend down / réseau)
  if (!error?.response) {
    return "Impossible de joindre le serveur. Vérifie ta connexion et que le backend est démarré, puis réessaie.";
  }

  const status = error.response.status;
  const detail = error.response.data?.detail;

  if (status === 401) return "Session expirée. Reconnecte-toi.";
  if (status === 403) return "Action non autorisée.";
  if (status === 404) return "Ressource introuvable.";
  if (status >= 500) {
    return detail
      ? `Erreur serveur : ${detail}`
      : "Erreur serveur. Réessaie dans un instant.";
  }

  // Détail backend si fourni, sinon message générique
  return detail || error?.message || "Une erreur est survenue.";
}
