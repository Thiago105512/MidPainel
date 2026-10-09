// ------------------------------------------------------------- WhatsApp

function linkWhatsApp(texto) {
  const numero = estado.loja && estado.loja.whatsapp;
  return numero ? `https://wa.me/${numero}?text=${encodeURIComponent(texto)}` : null;
}

/** `texto` pode ser uma função, para a mensagem refletir o estado na hora do clique (ex.: quantidade). */
function botaoWhatsApp(texto, rotulo, classe = "botao whatsapp", soIcone = false) {
  const gerar = typeof texto === "function" ? texto : () => texto;
  const url = linkWhatsApp(gerar());
  if (!url) return null;
  return h("a", { class: classe, href: url, target: "_blank", rel: "noopener", "aria-label": soIcone ? rotulo : null,
    onclick: (e) => { e.currentTarget.href = linkWhatsApp(gerar()); } },
  h("span", { "aria-hidden": "true" }, "💬"), soIcone ? null : ` ${rotulo}`);
}

function atualizarWhatsAppFlutuante() {
  const antigo = $("#whatsapp-flutuante");
  if (antigo) antigo.remove();
  const url = linkWhatsApp(estado.loja.whatsapp_mensagem || "Olá!");
  if (!url) return;
  document.body.append(h("a", { id: "whatsapp-flutuante", class: "whatsapp-flutuante", href: url, target: "_blank", rel: "noopener",
    "aria-label": "Atendimento pelo WhatsApp" }, h("span", { "aria-hidden": "true" }, "💬"), h("span", { class: "so-desktop" }, "Atendimento")));
}
