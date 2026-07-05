// Moli — module de marque (charte Le Relevé, moli.energy).
// Chargé via frontend.extra_module_url. Rôle unique : déclarer la fonte
// Archivo (variable, servie en local — aucune requête externe) pour que le
// thème Moli puisse la référencer. Les couleurs vivent dans le thème
// (frontend.themes.Moli, posé par patch_ha_config), PAS ici.
(() => {
  if (document.getElementById("moli-brand-fonts")) return;
  const style = document.createElement("style");
  style.id = "moli-brand-fonts";
  style.textContent = `
@font-face {
  font-family: "Archivo";
  src: url("/local/moli-cards/archivo-var.woff2") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}
`;
  document.head.appendChild(style);
})();
