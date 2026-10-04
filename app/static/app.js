"use strict";

/* Dashboard do Dupex. Todo texto vindo da API entra no DOM via textContent (nunca innerHTML). */

const API = "/api/v1";
const POR_PAGINA = 10;
const ETAPAS = ["emitida", "aceita", "liquidada"];
const ROTULO = { emitida: "Emitida", aceita: "Aceita", liquidada: "Liquidada", cancelada: "Cancelada" };
const FILTROS = [
  ["", "Todas"],
  ["emitida", "Emitidas"],
  ["aceita", "Aceitas"],
  ["liquidada", "Liquidadas"],
  ["cancelada", "Canceladas"],
];
const CAMPOS = {
  numero: "Número",
  valor: "Valor",
  emitente: "Emitente",
  sacado: "Sacado",
  data_vencimento: "Vencimento",
};

const estado = {
  token: lerToken(),
  filtro: "",
  pagina: 0,
  itens: [],
  total: 0,
  contagens: {},
  aberta: null,
  modoLogin: "entrar",
};

const $ = (seletor) => document.querySelector(seletor);

/* ---------- utilidades ---------- */

function el(tag, props = {}, ...filhos) {
  const no = document.createElement(tag);
  for (const [chave, valor] of Object.entries(props)) {
    if (valor == null || valor === false) continue;
    if (chave === "class") no.className = valor;
    else if (chave === "text") no.textContent = valor;
    else if (chave === "data") Object.assign(no.dataset, valor);
    else if (chave.startsWith("on")) no.addEventListener(chave.slice(2), valor);
    else no.setAttribute(chave, valor === true ? "" : valor);
  }
  no.append(...filhos.flat().filter((filho) => filho != null && filho !== false));
  return no;
}

function lerToken() {
  try {
    return sessionStorage.getItem("dupex.token");
  } catch {
    return null;
  }
}

function gravarToken(token) {
  try {
    if (token) sessionStorage.setItem("dupex.token", token);
    else sessionStorage.removeItem("dupex.token");
  } catch {
    /* armazenamento indisponível: a sessão vale só até recarregar a página */
  }
}

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const formatarValor = (valor) => moeda.format(Number(valor));

function partesData(iso) {
  const [ano, mes, dia] = iso.split("-").map(Number);
  return { ano, mes, dia };
}

function formatarData(iso) {
  const { ano, mes, dia } = partesData(iso);
  return `${String(dia).padStart(2, "0")}/${String(mes).padStart(2, "0")}/${ano}`;
}

function hojeISO(deslocamentoDias = 0) {
  const d = new Date();
  d.setDate(d.getDate() + deslocamentoDias);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function diasAteVencer(iso) {
  const alvo = partesData(iso);
  const hoje = partesData(hojeISO());
  const dia = (p) => Date.UTC(p.ano, p.mes - 1, p.dia) / 86_400_000;
  return dia(alvo) - dia(hoje);
}

function textoVencimento(duplicata) {
  if (duplicata.status === "liquidada" || duplicata.status === "cancelada") return null;
  const dias = diasAteVencer(duplicata.data_vencimento);
  if (dias < 0) return { texto: `Venceu há ${-dias} ${-dias === 1 ? "dia" : "dias"}`, vencida: true };
  if (dias === 0) return { texto: "Vence hoje", vencida: false };
  return { texto: `Vence em ${dias} ${dias === 1 ? "dia" : "dias"}`, vencida: false };
}

function parseValor(texto) {
  let v = texto.trim().replace(/^R\$\s*/i, "").replace(/\s/g, "");
  if (v.includes(",")) v = v.replace(/\./g, "").replace(",", ".");
  return /^\d+(\.\d{1,2})?$/.test(v) ? v : null;
}

function aviso(texto, tipo = "ok") {
  const area = $("#avisos");
  try {
    // O popover fica aberto o tempo todo (região de leitura estável). Quando há um diálogo
    // modal aberto, reabri-lo o põe de novo acima do diálogo na camada superior.
    if (!area.matches(":popover-open")) area.showPopover();
    else if (document.querySelector("dialog[open]")) {
      area.hidePopover();
      area.showPopover();
    }
  } catch {
    /* navegador sem suporte a popover: o aviso aparece, só pode ficar atrás de um diálogo */
  }
  const no = el("p", { class: `aviso ${tipo === "erro" ? "erro" : ""}`.trim(), text: texto });
  area.append(no);
  setTimeout(() => no.remove(), 4500);
}

/* ---------- API ---------- */

class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : "Erro na requisição");
    this.status = status;
    this.detail = detail;
  }
}

async function api(caminho, { metodo = "GET", corpo, formulario } = {}) {
  const cabecalhos = {};
  if (estado.token) cabecalhos.Authorization = `Bearer ${estado.token}`;

  let body;
  if (formulario) {
    body = new URLSearchParams(formulario);
  } else if (corpo) {
    cabecalhos["Content-Type"] = "application/json";
    body = JSON.stringify(corpo);
  }

  let resposta;
  try {
    resposta = await fetch(API + caminho, { method: metodo, headers: cabecalhos, body });
  } catch {
    throw new ApiError(0, "Não foi possível falar com a API. Confira se o servidor está no ar.");
  }

  if (resposta.status === 204) return null;
  let dados = null;
  try {
    dados = await resposta.json();
  } catch {
    /* corpo vazio ou não-JSON */
  }

  if (!resposta.ok) {
    if (resposta.status === 401 && estado.token) encerrarSessao("Sua sessão expirou. Entre novamente.");
    throw new ApiError(resposta.status, dados?.detail ?? "Erro inesperado. Tente novamente.");
  }
  return dados;
}

function traduzirErro(item) {
  const ctx = item.ctx ?? {};
  switch (item.type) {
    case "missing":
      return "Campo obrigatório.";
    case "string_too_short":
      return ctx.min_length === 1 ? "Campo obrigatório." : `Use pelo menos ${ctx.min_length} caracteres.`;
    case "string_too_long":
      return `Use no máximo ${ctx.max_length} caracteres.`;
    case "greater_than":
      return "Informe um valor maior que zero.";
    case "decimal_max_places":
      return "Use no máximo 2 casas decimais.";
    case "decimal_max_digits":
    case "decimal_whole_digits":
      return "Valor grande demais.";
    case "date_parsing":
    case "date_from_datetime_parsing":
    case "date_type":
      return "Data inválida.";
    case "value_error": {
      const msg = String(item.msg);
      if (msg.includes("passado")) return "O vencimento não pode estar no passado.";
      if (msg.includes("bytes")) return "A senha é longa demais (máximo de 72 bytes).";
      if (msg.includes("username")) return "Use apenas letras, números, '_', '.' e '-'.";
      return "Valor inválido.";
    }
    default:
      return "Valor inválido.";
  }
}

/** Converte o `detail` do FastAPI em { campo: mensagem } + mensagem geral. */
function interpretarErro(erro) {
  if (!(erro instanceof ApiError)) return { geral: "Algo deu errado. Tente novamente.", campos: {} };
  if (Array.isArray(erro.detail)) {
    const campos = {};
    for (const item of erro.detail) {
      const campo = item.loc?.[item.loc.length - 1];
      if (typeof campo === "string" && !(campo in campos)) campos[campo] = traduzirErro(item);
    }
    return { geral: null, campos };
  }
  return { geral: erro.message, campos: {} };
}

/* ---------- telas ---------- */

function mostrarTela(nome) {
  $("#tela-login").hidden = nome !== "login";
  $("#tela-painel").hidden = nome !== "painel";
}

function encerrarSessao(mensagem) {
  estado.token = null;
  gravarToken(null);
  fecharDialogos();
  mostrarTela("login");
  if (mensagem) mostrarErroLogin(mensagem);
}

function fecharDialogos() {
  for (const dlg of document.querySelectorAll("dialog[open]")) dlg.close();
}

/* ---------- entrar / criar conta ---------- */

function definirModoLogin(modo) {
  estado.modoLogin = modo;
  const criando = modo === "criar";
  $("#aba-entrar").setAttribute("aria-selected", String(!criando));
  $("#aba-entrar").tabIndex = criando ? -1 : 0;
  $("#aba-criar").setAttribute("aria-selected", String(criando));
  $("#aba-criar").tabIndex = criando ? 0 : -1;
  $("#form-login").setAttribute("aria-labelledby", criando ? "aba-criar" : "aba-entrar");
  $("#enviar-login").textContent = criando ? "Criar conta" : "Entrar";
  $("#dica-senha").hidden = !criando;
  $("#login-senha").autocomplete = criando ? "new-password" : "current-password";
  limparErroLogin();
}

function mostrarErroLogin(texto) {
  const no = $("#erro-login");
  no.textContent = texto;
  no.hidden = false;
}

function limparErroLogin() {
  $("#erro-login").hidden = true;
}

$("#aba-entrar").addEventListener("click", () => definirModoLogin("entrar"));
$("#aba-criar").addEventListener("click", () => definirModoLogin("criar"));
$("#aba-entrar").parentElement.addEventListener("keydown", (e) => {
  if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
  const alvo = estado.modoLogin === "entrar" ? "criar" : "entrar";
  definirModoLogin(alvo);
  $(alvo === "criar" ? "#aba-criar" : "#aba-entrar").focus();
});

$("#form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  limparErroLogin();
  const username = $("#login-usuario").value.trim();
  const password = $("#login-senha").value;
  if (!username || !password) return mostrarErroLogin("Informe usuário e senha.");

  const botao = $("#enviar-login");
  botao.disabled = true;
  try {
    if (estado.modoLogin === "criar") {
      await api("/auth/register", { metodo: "POST", corpo: { username, password } });
    }
    const token = await api("/auth/token", { metodo: "POST", formulario: { username, password } });
    estado.token = token.access_token;
    gravarToken(estado.token);
    $("#login-senha").value = "";
    await abrirPainel();
  } catch (erro) {
    const { geral, campos } = interpretarErro(erro);
    const detalhes = Object.entries(campos).map(([campo, msg]) => `${campo === "username" ? "Usuário" : "Senha"}: ${msg}`);
    mostrarErroLogin(geral ?? detalhes.join(" "));
  } finally {
    botao.disabled = false;
  }
});

$("#sair").addEventListener("click", () => {
  encerrarSessao();
  $("#login-usuario").focus();
});

/* ---------- painel ---------- */

async function abrirPainel() {
  const eu = await api("/auth/me");
  $("#nome-usuario").textContent = eu.username;
  mostrarTela("painel");
  await carregar();
}

async function carregar() {
  const area = $("#tabela-area");
  area.setAttribute("aria-busy", "true");
  try {
    await Promise.all([carregarPagina(), carregarContagens()]);
  } catch (erro) {
    aviso(interpretarErro(erro).geral ?? "Não foi possível carregar as duplicatas.", "erro");
  } finally {
    area.setAttribute("aria-busy", "false");
  }
  renderFiltros();
  renderTabela();
  renderPaginacao();
}

async function carregarPagina() {
  const params = new URLSearchParams({ limit: POR_PAGINA, offset: estado.pagina * POR_PAGINA });
  if (estado.filtro) params.set("status", estado.filtro);
  const pagina = await api(`/duplicatas?${params}`);

  // Excluiu o último item da página: volta uma.
  if (pagina.items.length === 0 && pagina.total > 0 && estado.pagina > 0) {
    estado.pagina -= 1;
    return carregarPagina();
  }
  estado.itens = pagina.items;
  estado.total = pagina.total;
}

async function carregarContagens() {
  const resultados = await Promise.all(
    FILTROS.map(([status]) => api(`/duplicatas?limit=1${status ? `&status=${status}` : ""}`)),
  );
  FILTROS.forEach(([status], i) => {
    estado.contagens[status] = resultados[i].total;
  });
}

function renderFiltros() {
  const nos = FILTROS.map(([status, rotulo]) =>
    el(
      "button",
      {
        type: "button",
        class: "filtro",
        role: "tab",
        "aria-selected": String(estado.filtro === status),
        tabindex: estado.filtro === status ? "0" : "-1",
        onclick: () => {
          estado.filtro = status;
          estado.pagina = 0;
          carregar();
        },
      },
      rotulo,
      el("span", { class: "filtro-total", text: String(estado.contagens[status] ?? 0) }),
    ),
  );
  $("#filtros").replaceChildren(...nos);
}

function trilha(status, classe = "") {
  const cancelada = status === "cancelada";
  const ate = cancelada ? -1 : ETAPAS.indexOf(status);
  return el(
    "ol",
    { class: `ciclo ${classe}`.trim(), "aria-hidden": "true" },
    ETAPAS.map((_, i) => el("li", { class: i <= ate ? "feita" : "" })),
  );
}

function renderTabela() {
  const corpo = $("#corpo-tabela");
  const vazio = estado.itens.length === 0;
  $("#tabela-area").querySelector("table").hidden = vazio;
  $("#vazio").hidden = !vazio;

  if (vazio) {
    const filtrando = estado.filtro !== "";
    $("#vazio-titulo").textContent = filtrando
      ? `Nenhuma duplicata ${ROTULO[estado.filtro].toLowerCase()}`
      : "Você ainda não emitiu duplicatas";
    $("#vazio-texto").textContent = filtrando
      ? "Escolha outro filtro ou emita uma nova duplicata."
      : "Emita a primeira para acompanhar aceite e liquidação por aqui.";
    $("#vazio-acao").hidden = filtrando;
    corpo.replaceChildren();
    return;
  }

  corpo.replaceChildren(...estado.itens.map(linha));
}

function linha(duplicata) {
  const venc = textoVencimento(duplicata);
  const abrir = () => abrirDetalhe(duplicata);

  return el(
    "tr",
    { role: "row", data: { status: duplicata.status }, onclick: abrir },
    el(
      "td",
      { role: "cell", class: "c-num" },
      el("button", {
        type: "button",
        class: "numero-link",
        text: duplicata.numero,
        "aria-label": `Abrir duplicata ${duplicata.numero}`,
        onclick: (e) => {
          e.stopPropagation();
          abrir();
        },
      }),
    ),
    el(
      "td",
      { role: "cell", class: "c-sac" },
      el("span", { class: "sacado-nome", text: duplicata.sacado }),
      el("span", { class: "sub", text: `Emitente: ${duplicata.emitente}` }),
    ),
    el(
      "td",
      { role: "cell", class: "c-ven" },
      el("span", { text: formatarData(duplicata.data_vencimento) }),
      venc && el("span", { class: `sub ${venc.vencida ? "vencida" : ""}`.trim(), text: venc.texto }),
    ),
    el("td", { role: "cell", class: "c-val num" }, el("span", { class: "valor", text: formatarValor(duplicata.valor) })),
    el(
      "td",
      { role: "cell", class: "c-sit situacao" },
      trilha(duplicata.status),
      el("span", { class: "situacao-nome", text: ROTULO[duplicata.status] }),
    ),
  );
}

function renderPaginacao() {
  const nav = $("#paginacao");
  nav.hidden = estado.total === 0;
  if (estado.total === 0) return;
  const de = estado.pagina * POR_PAGINA + 1;
  const ate = Math.min(de + estado.itens.length - 1, estado.total);
  $("#paginacao-resumo").textContent = `Mostrando ${de}–${ate} de ${estado.total}`;
  $("#pagina-anterior").disabled = estado.pagina === 0;
  $("#pagina-proxima").disabled = ate >= estado.total;
}

$("#pagina-anterior").addEventListener("click", () => {
  estado.pagina -= 1;
  carregar();
});
$("#pagina-proxima").addEventListener("click", () => {
  estado.pagina += 1;
  carregar();
});

/* ---------- emitir duplicata ---------- */

const dlgEmitir = $("#dlg-emitir");
const formEmitir = $("#form-emitir");

function abrirEmitir() {
  formEmitir.reset();
  limparErrosEmitir();
  $("#f-vencimento").min = hojeISO();
  $("#f-vencimento").value = hojeISO(30);
  dlgEmitir.showModal();
}

function limparErrosEmitir() {
  $("#erro-emitir").hidden = true;
  for (const nome of Object.keys(CAMPOS)) mostrarErroCampo(nome, null);
}

function mostrarErroCampo(nome, mensagem) {
  const no = $(`#erro-${nome}`);
  const entrada = formEmitir.elements[nome];
  no.textContent = mensagem ?? "";
  no.hidden = !mensagem;
  if (mensagem) entrada.setAttribute("aria-invalid", "true");
  else entrada.removeAttribute("aria-invalid");
}

$("#abrir-emitir").addEventListener("click", abrirEmitir);
$("#vazio-acao").addEventListener("click", abrirEmitir);

formEmitir.addEventListener("submit", async (e) => {
  e.preventDefault();
  limparErrosEmitir();

  const dados = Object.fromEntries(new FormData(formEmitir));
  const valor = parseValor(dados.valor);
  if (valor === null) {
    mostrarErroCampo("valor", "Informe um valor válido, como 1.500,00.");
    return formEmitir.elements.valor.focus();
  }

  const botao = $("#enviar-emitir");
  botao.disabled = true;
  try {
    const criada = await api("/duplicatas", { metodo: "POST", corpo: { ...dados, valor } });
    dlgEmitir.close();
    aviso(`Duplicata ${criada.numero} emitida`);
    estado.filtro = "";
    estado.pagina = 0;
    await carregar();
  } catch (erro) {
    if (erro instanceof ApiError && erro.status === 409) {
      mostrarErroCampo("numero", "Já existe uma duplicata com este número.");
      formEmitir.elements.numero.focus();
    } else {
      const { geral, campos } = interpretarErro(erro);
      for (const [campo, msg] of Object.entries(campos)) {
        if (campo in CAMPOS) mostrarErroCampo(campo, msg);
      }
      if (geral || Object.keys(campos).length === 0) {
        $("#erro-emitir").textContent = geral ?? "Não foi possível emitir a duplicata.";
        $("#erro-emitir").hidden = false;
      }
      formEmitir.querySelector('[aria-invalid="true"]')?.focus();
    }
  } finally {
    botao.disabled = false;
  }
});

/* ---------- detalhe e ações ---------- */

const dlgDetalhe = $("#dlg-detalhe");

const PROXIMA_ETAPA = {
  emitida: { para: "aceita", rotulo: "Registrar aceite", aviso: "Aceite registrado" },
  aceita: { para: "liquidada", rotulo: "Liquidar duplicata", aviso: "Duplicata liquidada" },
};

const SITUACAO_TEXTO = {
  emitida: "Aguardando o aceite do sacado.",
  aceita: "Aceita pelo sacado. Falta a liquidação.",
  liquidada: "Pagamento concluído.",
  cancelada: "Esta duplicata foi cancelada.",
};

function abrirDetalhe(duplicata) {
  estado.aberta = duplicata;
  renderDetalhe();
  if (!dlgDetalhe.open) dlgDetalhe.showModal();
}

function renderDetalhe() {
  const d = estado.aberta;
  $("#detalhe-titulo").textContent = `Duplicata ${d.numero}`;

  const ficha = el(
    "dl",
    { class: "ficha" },
    ...[
      ["Emitente", d.emitente],
      ["Sacado", d.sacado],
      ["Emissão", formatarData(d.data_emissao)],
      ["Vencimento", formatarData(d.data_vencimento)],
    ].flatMap(([nome, valor]) => [el("dt", { text: nome }), el("dd", { text: valor })]),
  );

  const venc = textoVencimento(d);
  const acoes = [];
  const proxima = PROXIMA_ETAPA[d.status];
  if (proxima) {
    acoes.push(
      el("button", {
        type: "button",
        class: "botao botao-primario",
        text: proxima.rotulo,
        onclick: () => mudarStatus(proxima.para, proxima.aviso),
      }),
    );
  }
  if (proxima) acoes.push(botaoConfirmado("Cancelar duplicata", "Confirmar cancelamento", () => mudarStatus("cancelada", "Duplicata cancelada")));
  acoes.push(botaoConfirmado("Excluir duplicata", "Confirmar exclusão", excluir));

  $("#detalhe-corpo").replaceChildren(
    el("p", { class: "detalhe-valor", text: formatarValor(d.valor) }),
    el(
      "div",
      { class: "detalhe-ciclo", data: { status: d.status } },
      trilha(d.status),
      el("p", { class: "situacao-nome", text: ROTULO[d.status] }),
      el("p", { class: "detalhe-situacao-texto", text: venc?.vencida ? `${SITUACAO_TEXTO[d.status]} ${venc.texto}.` : SITUACAO_TEXTO[d.status] }),
    ),
    ficha,
    el("div", { class: "acoes" }, ...acoes),
  );
}

/** Botão que pede um segundo clique antes de agir (volta ao normal após 5 s). */
function botaoConfirmado(rotulo, rotuloConfirmar, acao) {
  let temporizador;
  const botao = el("button", {
    type: "button",
    class: "botao botao-perigo",
    text: rotulo,
    onclick: async () => {
      if (!botao.classList.contains("confirmando")) {
        botao.classList.add("confirmando");
        botao.textContent = rotuloConfirmar;
        temporizador = setTimeout(() => {
          botao.classList.remove("confirmando");
          botao.textContent = rotulo;
        }, 5000);
        return;
      }
      clearTimeout(temporizador);
      botao.disabled = true;
      await acao();
      botao.disabled = false;
    },
  });
  return botao;
}

async function mudarStatus(novoStatus, mensagem) {
  const d = estado.aberta;
  try {
    estado.aberta = await api(`/duplicatas/${d.id}/status`, { metodo: "PATCH", corpo: { status: novoStatus } });
    renderDetalhe();
    aviso(mensagem);
    await carregar();
  } catch (erro) {
    aviso(interpretarErro(erro).geral ?? "Não foi possível atualizar o status.", "erro");
  }
}

async function excluir() {
  const d = estado.aberta;
  try {
    await api(`/duplicatas/${d.id}`, { metodo: "DELETE" });
    dlgDetalhe.close();
    aviso("Duplicata excluída");
    await carregar();
  } catch (erro) {
    aviso(interpretarErro(erro).geral ?? "Não foi possível excluir a duplicata.", "erro");
  }
}

/* ---------- diálogos: fechar ---------- */

for (const dlg of document.querySelectorAll("dialog")) {
  dlg.addEventListener("click", (e) => {
    // Clique no fundo (fora do conteúdo) ou em qualquer botão de fechar.
    if (e.target === dlg || e.target.closest("[data-fechar]")) dlg.close();
  });
}

/* ---------- início ---------- */

definirModoLogin("entrar");

(async function iniciar() {
  if (estado.token) {
    try {
      await abrirPainel();
      return;
    } catch {
      encerrarSessao();
    }
  }
  mostrarTela("login");
})();
