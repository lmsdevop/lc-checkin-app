const lista = document.getElementById("lista");
const busca = document.getElementById("busca");
const buscaWrap = document.getElementById("busca-wrap");
const toasts = document.getElementById("toasts");
const modal = document.getElementById("modal-nome");
const formNome = document.getElementById("form-nome");
const novoNome = document.getElementById("novo-nome");
const voltar = document.getElementById("voltar");
const ajuda = document.getElementById("ajuda");
const tipChamado = document.getElementById("tip-chamado");
const DURACAO_TOAST = 2000;

const estado = {
  etapa: "estaca",
  chamado: "",
  chamadoRotulo: "",
  estaca: "",
  ala: "",
  unidadeRotulo: "",
  registros: [],
  selecionado: null,
  opcoes: [],
};

function mostrarStatus(texto, tipo) {
  if (!texto) return;

  toasts.innerHTML = "";
  const toast = document.createElement("div");
  toast.className = `toast toast-${tipo || "erro"}`;
  toast.innerHTML = `
    <span class="toast-icone" aria-hidden="true">${tipo === "ok" ? "✓" : "!"}</span>
    <span class="toast-texto"></span>
  `;
  toast.querySelector(".toast-texto").textContent = texto;
  toasts.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("is-saindo");
    toast.addEventListener("animationend", () => toast.remove(), { once: true });
    setTimeout(() => toast.remove(), 400);
  }, DURACAO_TOAST);
}

function marcarPasso(etapa) {
  document.querySelectorAll(".steps li").forEach((li) => {
    li.classList.toggle("is-current", li.dataset.step === etapa);
  });
}

function definirCabecalho(titulo, subtitulo) {
  document.getElementById("painel-titulo").textContent = titulo;
  document.getElementById("painel-sub").textContent = subtitulo;
}

async function carregarOpcoes() {
  const params = new URLSearchParams();
  if (estado.estaca) params.set("estaca", estado.estaca);
  if (estado.ala) params.set("ala", estado.ala);
  if (estado.chamado) params.set("chamado", estado.chamado);
  const resposta = await fetch(`/api/opcoes?${params.toString()}`);
  if (!resposta.ok) throw new Error("Não foi possível ler a planilha.");
  return resposta.json();
}

function esc(texto) {
  return String(texto)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderLista(itens, onPick) {
  lista.classList.remove("sem-rolagem");
  const normalizados = itens.map((item) =>
    typeof item === "string" ? { valor: item, rotulo: item } : item
  );
  buscaWrap.hidden = normalizados.length < 8;
  const filtro = busca.value.trim().toLowerCase();
  const visiveis = normalizados.filter((item) => item.rotulo.toLowerCase().includes(filtro));
  lista.innerHTML = "";
  if (!visiveis.length) {
    lista.innerHTML = `<p class="empty">Nenhuma opção encontrada.</p>`;
    return;
  }
  visiveis.forEach((item) => {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "choice";
    botao.textContent = item.rotulo;
    botao.addEventListener("click", () => onPick(item.valor));
    lista.appendChild(botao);
  });
}

function atualizarVoltar() {
  voltar.hidden = estado.etapa === "estaca" || estado.etapa === "sucesso";
  const chamadoComLista = estado.etapa === "chamado" && estado.opcoes.length > 0;
  ajuda.hidden = !chamadoComLista;
  tipChamado.hidden = !chamadoComLista;
}

async function etapaEstaca() {
  estado.etapa = "estaca";
  estado.chamado = "";
  estado.chamadoRotulo = "";
  estado.estaca = "";
  estado.ala = "";
  estado.unidadeRotulo = "";
  estado.selecionado = null;
  document.body.classList.remove("is-done");
  atualizarVoltar();
  marcarPasso("estaca");
  definirCabecalho("De qual estaca você é?", "Toque na sua estaca para continuar.");
  busca.value = "";
  const dados = await carregarOpcoes();
  estado.opcoes = dados.estacas;
  renderLista(estado.opcoes, async (item) => {
    estado.estaca = item;
    await etapaUnidade();
  });
}

async function etapaUnidade() {
  estado.etapa = "unidade";
  estado.chamado = "";
  estado.chamadoRotulo = "";
  estado.ala = "";
  estado.unidadeRotulo = "";
  atualizarVoltar();
  marcarPasso("unidade");
  definirCabecalho("Qual é a sua unidade?", `Estaca ${estado.estaca} — toque em Estaca ou na sua ala.`);
  busca.value = "";
  const dados = await carregarOpcoes();
  estado.opcoes = dados.unidades;
  renderLista(estado.opcoes, async (item) => {
    estado.ala = item;
    estado.unidadeRotulo = item;
    await etapaChamado();
  });
}

async function etapaChamado() {
  estado.etapa = "chamado";
  estado.chamado = "";
  estado.chamadoRotulo = "";
  estado.opcoes = [];
  marcarPasso("chamado");
  definirCabecalho("Qual é o seu chamado?", `${estado.unidadeRotulo} · Estaca ${estado.estaca}`);
  busca.value = "";
  const dados = await carregarOpcoes();
  estado.opcoes = dados.chamados || [];
  atualizarVoltar();
  if (!estado.opcoes.length) {
    renderUnidadeCompleta();
    return;
  }
  renderLista(estado.opcoes, async (item) => {
    estado.chamado = item;
    const escolhido = estado.opcoes.find((opcao) => (opcao.valor || opcao) === item);
    estado.chamadoRotulo = (escolhido && escolhido.rotulo) || item;
    await etapaRegistros();
  });
}

function renderUnidadeCompleta() {
  buscaWrap.hidden = true;
  lista.classList.add("sem-rolagem");
  const estaca = estado.estaca || "sua estaca";
  const unidade = estado.unidadeRotulo || "sua unidade";
  lista.innerHTML = `
    <article class="help-card">
      <p class="help-kicker">Check-in desta unidade</p>
      <h3>Todo mundo de ${esc(unidade)} já fez check-in</h3>
      <p>
        Não restam chamados pendentes nesta unidade da
        <strong>Estaca ${esc(estaca)}</strong>.
      </p>
      <p>
        Se a sua presença ainda não foi registrada, ou se houver qualquer dúvida,
        procure a mesa da <strong>Estaca ${esc(estaca)}</strong> na entrada da capela.
      </p>
    </article>
  `;
}

function renderAjudaChamado() {
  estado.etapa = "ajuda-chamado";
  atualizarVoltar();
  buscaWrap.hidden = true;
  definirCabecalho("Sem problema — vamos te ajudar", "Seu chamado pode não estar nesta lista.");
  lista.classList.add("sem-rolagem");
  const estaca = estado.estaca || "sua estaca";
  const unidade = estado.unidadeRotulo || "sua unidade";
  lista.innerHTML = `
    <article class="help-card">
      <p class="help-kicker">Precisa de apoio na recepção</p>
      <h3>Procure a mesa da Estaca ${esc(estaca)}</h3>
      <p>
        Não se preocupe. Às vezes o chamado não aparece porque já foi feito o check-in,
        o nome está em outra unidade ou ainda não está nesta lista.
      </p>
      <p>
        Vá até a <strong>entrada da capela</strong> e procure a mesa da
        <strong>Estaca ${esc(estaca)}</strong>. Diga que você é de
        <strong>${esc(unidade)}</strong> e que não encontrou o chamado no aplicativo.
        A equipe registra você na hora.
      </p>
      <button type="button" class="ghost" id="btn-voltar-lista">Voltar para a lista de chamados</button>
    </article>
  `;
  document.getElementById("btn-voltar-lista").addEventListener("click", () => etapaChamado());
}

async function etapaRegistros() {
  const dados = await carregarOpcoes();
  estado.registros = dados.registros || [];
  if (!estado.registros.length) {
    mostrarStatus("Nenhuma linha encontrada com essa combinação.", "erro");
    await etapaEstaca();
    return;
  }
  if (estado.registros.length === 1) {
    estado.selecionado = estado.registros[0];
    renderConfirmacao();
    return;
  }
  estado.etapa = "pessoa";
  marcarPasso("confirmar");
  atualizarVoltar();
  definirCabecalho("Qual desses é você?", "Encontramos mais de um registro para essa combinação.");
  busca.value = "";
  buscaWrap.hidden = false;
  lista.classList.remove("sem-rolagem");
  lista.innerHTML = "";
  estado.registros.forEach((reg) => {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "choice";
    botao.innerHTML = `${esc(reg.nome)}<small>${esc(reg.chamado)} · ${esc(reg.estaca)}</small>`;
    botao.addEventListener("click", () => {
      estado.selecionado = reg;
      renderConfirmacao();
    });
    lista.appendChild(botao);
  });
}

function renderConfirmacao() {
  const reg = estado.selecionado;
  estado.etapa = "confirmar";
  marcarPasso("confirmar");
  atualizarVoltar();
  definirCabecalho("Confira seus dados", "Se estiver tudo certo, confirme sua presença.");
  buscaWrap.hidden = true;
  lista.classList.add("sem-rolagem");
  lista.innerHTML = `
    <article class="card">
      <div class="card-top">
        <p class="kicker">Registro localizado</p>
        <h2>${esc(reg.nome)}</h2>
      </div>
      <dl class="meta">
        <div><dt>Chamado</dt><dd>${esc(reg.chamado)}</dd></div>
        <div><dt>Estaca</dt><dd>${esc(reg.estaca)}</dd></div>
        <div><dt>Ala</dt><dd>${esc(reg.ala_rotulo)}</dd></div>
      </dl>
      <div class="actions">
        <button class="solid" id="btn-ok">Sim, sou eu — confirmar presença</button>
        <button class="ghost" id="btn-nome">Corrigir meu nome</button>
        ${reg.pode_alterar_chamado ? '<button class="ghost" id="btn-chamado">Alterar chamado</button>' : ""}
        <button class="warn" id="btn-de-novo">Escolher de novo</button>
      </div>
    </article>
  `;
  document.getElementById("btn-ok").addEventListener("click", finalizar);
  document.getElementById("btn-nome").addEventListener("click", () => {
    novoNome.value = reg.nome;
    modal.showModal();
  });
  const btnChamado = document.getElementById("btn-chamado");
  if (btnChamado) btnChamado.addEventListener("click", renderAlterarChamado);
  document.getElementById("btn-de-novo").addEventListener("click", () => {
    mostrarStatus("");
    etapaEstaca();
  });
}

function renderAlterarChamado() {
  const reg = estado.selecionado;
  estado.etapa = "alterar-chamado";
  atualizarVoltar();
  definirCabecalho("Quem veio no lugar?", "Só o presidente ou bispo estava na lista; escolha o chamado de quem está aqui.");
  buscaWrap.hidden = true;
  lista.classList.remove("sem-rolagem");
  lista.innerHTML = "";
  (reg.opcoes_chamado || []).forEach((opcao) => {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = `choice${opcao.atual ? " is-atual" : ""}`;
    botao.innerHTML = `${esc(opcao.rotulo)}${opcao.atual ? "<small>Este é o chamado registrado agora</small>" : ""}`;
    botao.addEventListener("click", () => alterarChamado(opcao.valor));
    lista.appendChild(botao);
  });
}

async function alterarChamado(chamado) {
  const resposta = await fetch("/api/chamado", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      row: estado.selecionado.row,
      estaca: estado.selecionado.estaca,
      chamado,
    }),
  });
  const dados = await resposta.json();
  if (!resposta.ok) {
    mostrarStatus(dados.erro || "Não foi possível alterar o chamado.", "erro");
    return;
  }
  estado.selecionado = dados.registro;
  mostrarStatus("Chamado atualizado na planilha.", "ok");
  renderConfirmacao();
}

async function finalizar() {
  mostrarStatus("");
  const resposta = await fetch("/api/checkin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      row: estado.selecionado.row,
      estaca: estado.selecionado.estaca,
    }),
  });
  const dados = await resposta.json();
  if (!resposta.ok) {
    mostrarStatus(dados.erro || "Não foi possível finalizar o check-in.", "erro");
    return;
  }
  estado.etapa = "sucesso";
  estado.selecionado = dados.registro;
  atualizarVoltar();
  buscaWrap.hidden = true;
  document.body.classList.add("is-done");
  marcarPasso("sucesso");
  definirCabecalho("Presença confirmada", "Mostre esta tela na recepção.");
  lista.classList.add("sem-rolagem");
  lista.innerHTML = renderSucesso(dados.registro, dados.hora);
}

function renderSucesso(reg, hora) {
  return `
    <div class="done">
      <div class="seal" role="img" aria-label="Check-in confirmado">
        <svg viewBox="0 0 52 52" aria-hidden="true">
          <circle class="seal-ring" cx="26" cy="26" r="24" />
          <path class="seal-tick" d="M15 27.5l7.5 7.5L37.5 19" />
        </svg>
      </div>
      <p class="done-kicker">Check-in confirmado · ${esc(hora)}</p>
      <h2>${esc(reg.nome)}</h2>
      <div class="done-tags">
        <span>${esc(reg.chamado)}</span>
        <span>${esc(reg.estaca)}</span>
        <span>${esc(reg.ala_rotulo)}</span>
      </div>
      <p class="welcome">
        Seja bem-vindo(a) ao Conselho de Liderança! Apresente esta tela na recepção,
        pegue seu lanche e tenha uma ótima reunião.
      </p>
      <a
        class="cta-orientacoes"
        href="https://canva.link/x6bs2hhmg5342tw"
        target="_blank"
        rel="noopener noreferrer"
      >
        <span class="cta-kicker">Antes de começar</span>
        <strong>Ver orientações do conselho</strong>
        <span class="cta-hint">Toque aqui para o guia do encontro</span>
      </a>
      <p class="done-note">Sua presença já está registrada. Não é necessário fazer outro check-in.</p>
    </div>
  `;
}

document.getElementById("cancelar-nome").addEventListener("click", () => modal.close());

formNome.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const nome = novoNome.value.trim();
  if (!nome) return;
  const resposta = await fetch("/api/nome", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      row: estado.selecionado.row,
      estaca: estado.selecionado.estaca,
      nome,
    }),
  });
  const dados = await resposta.json();
  if (!resposta.ok) {
    mostrarStatus(dados.erro || "Não foi possível atualizar o nome.", "erro");
    return;
  }
  estado.selecionado = dados.registro;
  modal.close();
  mostrarStatus("Nome atualizado na planilha.", "ok");
  renderConfirmacao();
});

ajuda.addEventListener("click", () => {
  mostrarStatus("");
  renderAjudaChamado();
});

voltar.addEventListener("click", async () => {
  mostrarStatus("");
  if (estado.etapa === "unidade") await etapaEstaca();
  else if (estado.etapa === "chamado") await etapaUnidade();
  else if (estado.etapa === "ajuda-chamado") await etapaChamado();
  else if (estado.etapa === "alterar-chamado") renderConfirmacao();
  else if (estado.etapa === "pessoa" || estado.etapa === "confirmar") await etapaChamado();
});

busca.addEventListener("input", () => {
  if (["estaca", "unidade", "chamado"].includes(estado.etapa)) {
    renderLista(estado.opcoes, async (item) => {
      if (estado.etapa === "estaca") {
        estado.estaca = item;
        await etapaUnidade();
      } else if (estado.etapa === "unidade") {
        estado.ala = item;
        estado.unidadeRotulo = item;
        await etapaChamado();
      } else if (estado.etapa === "chamado") {
        estado.chamado = item;
        const escolhido = estado.opcoes.find((opcao) => (opcao.valor || opcao) === item);
        estado.chamadoRotulo = (escolhido && escolhido.rotulo) || item;
        await etapaRegistros();
      }
    });
  }
});

etapaEstaca().catch((erro) => mostrarStatus(erro.message, "erro"));
