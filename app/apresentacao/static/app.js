/* Comportamentos da interface (sem dependências). Tudo é progressivo: o sistema funciona sem JS*/
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  /* menu lateral no celular */
  const alternarMenu = () => document.body.classList.toggle("menu-aberto");
  const btn = $("#menu-btn");
  if (btn) btn.addEventListener("click", alternarMenu);
  const overlay = $("#overlay");
  if (overlay) overlay.addEventListener("click", () => document.body.classList.remove("menu-aberto"));

  /* mensagens: fechar e sumir sozinhas (as de sucesso) */
  $$(".flash").forEach((el) => {
    const x = $(".flash-x", el);
    if (x) x.addEventListener("click", () => el.remove());
    if (el.classList.contains("ok")) {
      setTimeout(() => { el.classList.add("some"); setTimeout(() => el.remove(), 500); }, 5000);
    }
  });

  /* máscaras de digitação */
  const digitos = (v) => v.replace(/\D/g, "");
  const mascaras = {
    cpf: (v) => digitos(v).slice(0, 11)
      .replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d{1,2})$/, "$1-$2"),
    cnpj: (v) => digitos(v).slice(0, 14)
      .replace(/(\d{2})(\d)/, "$1.$2").replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d)/, "$1/$2").replace(/(\d{4})(\d{1,2})$/, "$1-$2"),
    tel: (v) => {
      const d = digitos(v).slice(0, 11);
      if (d.length <= 2) return d ? "(" + d : "";
      if (d.length <= 6) return "(" + d.slice(0, 2) + ") " + d.slice(2);
      if (d.length <= 10) return "(" + d.slice(0, 2) + ") " + d.slice(2, 6) + "-" + d.slice(6);
      return "(" + d.slice(0, 2) + ") " + d.slice(2, 7) + "-" + d.slice(7);
    },
    placa: (v) => v.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 7),
  };
  const aplicarMascara = (el) => {
    const m = mascaras[el.dataset.mask];
    if (m) el.value = m(el.value);
  };
  $$("[data-mask]").forEach((el) => {
    el.addEventListener("input", () => aplicarMascara(el));
    aplicarMascara(el);
  });

  /* formulário de cliente: CPF x CNPJ conforme o tipo */
  const tipo = $("#tipo_cliente");
  const doc = $("#documento");
  if (tipo && doc) {
    const rotulo = $("#rotulo-documento");
    const atualizar = () => {
      const pj = tipo.value === "J";
      doc.dataset.mask = pj ? "cnpj" : "cpf";
      doc.placeholder = pj ? "00.000.000/0000-00" : "000.000.000-00";
      if (rotulo) rotulo.textContent = (pj ? "CNPJ" : "CPF") + " *";
      aplicarMascara(doc);
    };
    tipo.addEventListener("change", atualizar);
    atualizar();
  }

  /* filtros que enviam ao mudar */
  $$("[data-autosubmit]").forEach((el) => el.addEventListener("change", () => el.form.submit()));

  /* confirmação antes de ações sensíveis */
  $$("form[data-confirm]").forEach((f) =>
    f.addEventListener("submit", (e) => { if (!window.confirm(f.dataset.confirm)) e.preventDefault(); }));

  /* selects que preenchem outro campo a partir de data-* da opção escolhida */
  $$("select[data-preenche]").forEach((sel) => {
    const alvo = $(sel.dataset.preenche);
    const attr = sel.dataset.attr;
    if (!alvo) return;
    sel.addEventListener("change", () => {
      const op = sel.options[sel.selectedIndex];
      const v = op && op.dataset[attr];
      if (v !== undefined && v !== "") alvo.value = v;
    });
  });

  /* pedido de peças: subtotais e total em tempo real */
  const moeda = (n) => n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const qtds = $$(".js-qtd");
  if (qtds.length) {
    const total = $("#total-pedido");
    const recalcular = () => {
      let soma = 0;
      qtds.forEach((i) => {
        const sub = (parseInt(i.value, 10) || 0) * parseFloat(i.dataset.preco);
        soma += sub;
        const cel = $("#sub-" + i.dataset.id);
        if (cel) cel.textContent = sub ? moeda(sub) : "—";
      });
      if (total) total.textContent = moeda(soma);
    };
    qtds.forEach((i) => i.addEventListener("input", recalcular));
    recalcular();
  }
})();
