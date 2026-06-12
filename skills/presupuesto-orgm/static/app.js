const TEMPLATE_PATHS = {
  header: 'templates/header.html',
  footer: 'templates/footer.html',
  body: 'templates/body.html',
  partida: 'templates/partida.html',
  subtotalPartidas: 'templates/subtotal_partidas.html',
  indirecto: 'templates/indirecto.html',
  total: 'templates/total.html',
  monedaAlt: 'templates/moneda_alt.html',
  notasConsideraciones: 'templates/notas-consideraciones.html',
  glosarioUnidades: 'templates/glosario-unidades.html',
};

const DEFAULT_LOGO_SRC = 'assets/logo.png';

function setStatus(message) {
  const node = document.getElementById('render-status');
  if (node) node.textContent = message;
}

async function fetchText(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`No se pudo cargar ${path}: ${response.status}`);
  return response.text();
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`No se pudo cargar ${path}: ${response.status}`);
  return response.json();
}

async function loadTemplates() {
  const entries = await Promise.all(Object.entries(TEMPLATE_PATHS).map(async ([key, path]) => [key, await fetchText(path)]));
  return Object.fromEntries(entries);
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function renderTemplate(template, data) {
  return template.replace(/{{\s*([\w.]+)\s*}}/g, (_, key) => {
    const value = key.split('.').reduce((current, part) => current?.[part], data);
    return value == null ? '' : String(value);
  });
}

function formatMoney(value, currency) {
  const symbol = currency.symbol || (currency.base === 'DOP' ? 'RD$' : currency.base);
  return `${symbol} ${Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatUsd(value, currency) {
  const rate = Number(currency.usdRate || 0);
  if (!rate) return 'US$ 0.00';
  return `US$ ${(Number(value || 0) / rate).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function calculateBudget(raw) {
  const currency = raw.currency || { base: 'DOP', symbol: 'RD$' };
  const partidas = (raw.partidas || []).map((partida) => {
    const subcategories = (partida.subcategories || []).map((subcategory) => {
      const items = (subcategory.items || []).map((item) => {
        const quantity = Number(item.quantity || 0);
        const unitPrice = Number(item.unitPrice || item.unit_price || 0);
        const total = Number(item.total ?? quantity * unitPrice);
        return { ...item, quantity, unitPrice, total };
      });
      const subtotal = items.reduce((sum, item) => sum + item.total, 0);
      return { ...subcategory, items, subtotal };
    });
    const total = subcategories.reduce((sum, subcategory) => sum + subcategory.subtotal, 0);
    return { ...partida, subcategories, total };
  });
  const subtotalPartidas = partidas.reduce((sum, partida) => sum + partida.total, 0);
  const indirectos = (raw.indirectos || []).map((indirecto) => {
    const type = indirecto.type || 'percent';
    const value = Number(indirecto.value || 0);
    const amount = type === 'fixed' ? value : subtotalPartidas * (value / 100);
    const typeLabel = type === 'fixed' ? 'Monto fijo' : `${value.toFixed(2)}%`;
    return { ...indirecto, type, value, amount, typeLabel };
  });
  const totalIndirectos = indirectos.reduce((sum, indirecto) => sum + indirecto.amount, 0);
  const itbisPercent = Number(raw.taxes?.itbisPercent ?? 18);
  const baseItbis = subtotalPartidas + totalIndirectos;
  const itbis = baseItbis * (itbisPercent / 100);
  return { ...raw, currency, partidas, indirectos, totals: { subtotalPartidas, totalIndirectos, itbisPercent, baseItbis, itbis, totalGeneral: baseItbis + itbis } };
}

function renderSubcategory(subcategory, currency) {
  const rows = (subcategory.items || []).map((item) => `
    <tr>
      <td class="text-center">${escapeHtml(item.code)}</td>
      <td>${escapeHtml(item.description)}</td>
      <td class="text-center">${escapeHtml(item.unit)}</td>
      <td class="text-right">${Number(item.quantity).toLocaleString('en-US', { maximumFractionDigits: 2 })}</td>
      <td class="text-right">${formatMoney(item.unitPrice, currency)}</td>
      <td class="text-right">${formatMoney(item.total, currency)}</td>
    </tr>`).join('');
  return `<section class="subcategory" data-subcategory-code="${escapeHtml(subcategory.code)}">
    <div class="subcategory-title"><span>${escapeHtml(subcategory.code)} ${escapeHtml(subcategory.title)}</span><span>${formatMoney(subcategory.subtotal, currency)}</span></div>
    <table class="budget-table"><thead><tr><th>Código</th><th>Descripción</th><th>Und.</th><th class="text-right">Cant.</th><th class="text-right">P. unit.</th><th class="text-right">Total</th></tr></thead><tbody>${rows}</tbody></table>
    <div class="subtotal-row"><span>Subtotal</span><span>${formatMoney(subcategory.subtotal, currency)}</span></div>
  </section>`;
}

function renderPartidaBlock(partida, templates, currency) {
  const subcategories = (partida.subcategories || []).map((subcategory) => renderSubcategory(subcategory, currency)).join('');
  return renderTemplate(templates.partida, { code: escapeHtml(partida.code), title: escapeHtml(partida.title), description: escapeHtml(partida.description), subcategories, totalFormatted: formatMoney(partida.total, currency) });
}

function renderSubtotalPartidasBlock(budget, templates) {
  return renderTemplate(templates.subtotalPartidas, { subtotalPartidasFormatted: formatMoney(budget.totals.subtotalPartidas, budget.currency) });
}

function renderIndirectosBlock(budget, templates) {
  const rows = budget.indirectos.map((indirecto) => `<tr><td>${escapeHtml(indirecto.name)}</td><td class="text-right">${formatMoney(budget.totals.subtotalPartidas, budget.currency)}</td><td class="text-right">${escapeHtml(indirecto.typeLabel)}</td><td class="text-right">${formatMoney(indirecto.amount, budget.currency)}</td></tr>`).join('');
  return renderTemplate(templates.indirecto, { rows, totalIndirectosFormatted: formatMoney(budget.totals.totalIndirectos, budget.currency) });
}

function renderTotalBlock(budget, templates) {
  const t = budget.totals;
  return renderTemplate(templates.total, { subtotalPartidasFormatted: formatMoney(t.subtotalPartidas, budget.currency), totalIndirectosFormatted: formatMoney(t.totalIndirectos, budget.currency), baseItbisFormatted: formatMoney(t.baseItbis, budget.currency), itbisPercent: t.itbisPercent.toLocaleString('en-US', { maximumFractionDigits: 2 }), itbisFormatted: formatMoney(t.itbis, budget.currency), totalGeneralFormatted: formatMoney(t.totalGeneral, budget.currency) });
}

function renderMonedaAltBlock(budget, templates) {
  const { currency, totals } = budget;
  if (!currency.showUsdConversion || !Number(currency.usdRate || 0)) return null;
  return renderTemplate(templates.monedaAlt, { exchangeRate: `1 USD = ${Number(currency.usdRate).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${escapeHtml(currency.base || 'DOP')}`, subtotalPartidasAlt: formatUsd(totals.subtotalPartidas, currency), totalIndirectosAlt: formatUsd(totals.totalIndirectos, currency), baseItbisAlt: formatUsd(totals.baseItbis, currency), itbisPercent: totals.itbisPercent.toLocaleString('en-US', { maximumFractionDigits: 2 }), itbisAlt: formatUsd(totals.itbis, currency), totalGeneralAlt: formatUsd(totals.totalGeneral, currency) });
}

function renderNotesList(notes) {
  return `<ul class="notes-list">${notes.map((note) => `<li>${escapeHtml(note)}</li>`).join('')}</ul>`;
}

function renderNotasConsideracionesBlocks(budget, templates) {
  const generalNotes = budget.consideraciones?.generales || [];
  const partidasWithNotes = (budget.partidas || []).filter((partida) => Array.isArray(partida.consideraciones) && partida.consideraciones.length > 0);
  if (!generalNotes.length && !partidasWithNotes.length) return [];
  const blocks = [{ type: 'notas-consideraciones', forceNewPage: true, html: renderTemplate(templates.notasConsideraciones, { generalNotes: generalNotes.length ? renderNotesList(generalNotes) : '<p class="notes-empty">Sin consideraciones generales.</p>', partidaNotes: partidasWithNotes.length ? '' : '<p class="notes-empty">Sin consideraciones por partida.</p>' }) }];
  for (const partida of partidasWithNotes) {
    blocks.push({ type: 'notas-consideraciones', html: `<article class="notes-partida notes-partida-block" data-block-type="notas-partida"><h4>${escapeHtml(partida.code)}. ${escapeHtml(partida.title)}</h4>${renderNotesList(partida.consideraciones)}</article>` });
  }
  return blocks;
}

const UNIT_GLOSSARY = { gl: ['Global / partida alzada', 'Alcance completo que no se mide por longitud, área, volumen o unidad individual.'], m2: ['Metro cuadrado', 'Áreas de piso, techo, pintura, cerámica, replanteo o terminaciones.'], 'm2-eq': ['Metro cuadrado equivalente', 'Área convertida a condición equivalente de trabajo.'], m3: ['Metro cúbico', 'Volúmenes de excavación, relleno, hormigón o material.'], 'm3-km': ['Metro cúbico-kilómetro', 'Acarreo o transporte medido por volumen y distancia.'], m3c: ['Metro cúbico compactado', 'Relleno regado, nivelado y compactado.'], ml: ['Metro lineal', 'Elementos medidos por longitud.'], m: ['Metro', 'Elementos medidos por longitud.'], p2: ['Pie cuadrado', 'Área comercial de ventanas, puertas de aluminio y vidrios.'], pl: ['Pie lineal', 'Cables o conductores medidos por longitud.'], qq: ['Quintal', 'Peso de acero de refuerzo.'], rollo: ['Rollo', 'Material suministrado comercialmente por rollo.'], und: ['Unidad', 'Piezas, equipos, accesorios o elementos contables individualmente.'] };

function renderGlosarioUnidadesBlock(budget, templates) {
  const units = [...new Set((budget.partidas || []).flatMap((p) => (p.subcategories || []).flatMap((s) => (s.items || []).map((i) => String(i.unit || '')).filter(Boolean))))].sort((a, b) => a.localeCompare(b, 'es'));
  if (!units.length) return null;
  const rows = units.map((unit) => { const d = UNIT_GLOSSARY[unit] || ['Unidad usada en el presupuesto', 'Ver descripción de la partida correspondiente.']; return `<tr><td>${escapeHtml(unit)}</td><td>${escapeHtml(d[0])}</td><td>${escapeHtml(d[1])}</td></tr>`; }).join('');
  return renderTemplate(templates.glosarioUnidades, { rows });
}

function buildBlocks(budget, templates) {
  const monedaAltBlock = renderMonedaAltBlock(budget, templates);
  return [
    ...budget.partidas.map((partida) => ({ type: 'partida', html: renderPartidaBlock(partida, templates, budget.currency), partida })),
    { type: 'subtotal-partidas', html: renderSubtotalPartidasBlock(budget, templates) },
    { type: 'indirectos', html: renderIndirectosBlock(budget, templates) },
    { type: 'total', html: renderTotalBlock(budget, templates) },
    ...(monedaAltBlock ? [{ type: 'moneda-alt', html: monedaAltBlock }] : []),
    ...renderNotasConsideracionesBlocks(budget, templates),
    { type: 'glosario-unidades', html: renderGlosarioUnidadesBlock(budget, templates) },
  ].filter((block) => block.html);
}

function createPageShell(templates, budget, pageNumber, pageCount = '{{pageCount}}') {
  const project = budget.project || {};
  const header = renderTemplate(templates.header, { logoSrc: escapeHtml(budget.logoSrc || DEFAULT_LOGO_SRC), companyName: escapeHtml(budget.companyName || ''), documentTitle: escapeHtml(project.documentTitle || 'Presupuesto'), projectName: escapeHtml(project.name || ''), voltage: escapeHtml(project.voltage || ''), location: escapeHtml(project.location || ''), client: escapeHtml(project.client || ''), date: escapeHtml(project.date || ''), revision: escapeHtml(project.revision || ''), currencyBase: escapeHtml(budget.currency?.base || 'DOP') });
  const footer = renderTemplate(templates.footer, { companyName: escapeHtml(budget.companyName || ''), pageNumber, pageCount });
  const html = renderTemplate(templates.body, { header, content: '', footer });
  const wrapper = document.createElement('div');
  wrapper.innerHTML = html.trim();
  return wrapper.firstElementChild;
}

function getBody(page) { return page.querySelector('.page-body'); }

function measureBlockHeight(blockHtml, templates, budget) {
  const measureRoot = document.getElementById('measure-root');
  const page = createPageShell(templates, budget, 1, 1);
  const body = getBody(page);
  body.innerHTML = blockHtml;
  measureRoot.replaceChildren(page);
  const height = body.firstElementChild.getBoundingClientRect().height;
  measureRoot.replaceChildren();
  return height;
}

function getAvailableBodyHeight(templates, budget) {
  const measureRoot = document.getElementById('measure-root');
  const page = createPageShell(templates, budget, 1, 1);
  measureRoot.replaceChildren(page);
  const height = getBody(page).getBoundingClientRect().height;
  measureRoot.replaceChildren();
  return height;
}

function splitOversizedPartida(block, templates, budget) {
  if (block.type !== 'partida' || !block.partida?.subcategories?.length) return [block];
  return block.partida.subcategories.map((subcategory, index) => ({ type: 'partida-subcategory', html: renderPartidaBlock({ ...block.partida, title: `${block.partida.title} ${index > 0 ? '(continuación)' : ''}`.trim(), description: index === 0 ? block.partida.description : 'Continuación de partida por límite de espacio de impresión.', subcategories: [subcategory], total: subcategory.subtotal }, templates, budget.currency) }));
}

function paginateBlocks(blocks, templates, budget) {
  const availableHeight = getAvailableBodyHeight(templates, budget);
  const pages = [];
  let currentPage = createPageShell(templates, budget, 1);
  let currentBody = getBody(currentPage);
  let usedHeight = 0;
  const pushPage = () => { pages.push(currentPage); currentPage = createPageShell(templates, budget, pages.length + 1); currentBody = getBody(currentPage); usedHeight = 0; };
  const appendBlock = (blockHtml, blockHeight) => { const wrapper = document.createElement('div'); wrapper.innerHTML = blockHtml.trim(); currentBody.appendChild(wrapper.firstElementChild); usedHeight += blockHeight; };
  for (const block of blocks) {
    if (block.forceNewPage && usedHeight > 0) pushPage();
    const blockHeight = measureBlockHeight(block.html, templates, budget);
    if (blockHeight > availableHeight && block.type === 'partida') {
      for (const splitBlock of splitOversizedPartida(block, templates, budget)) {
        const splitHeight = measureBlockHeight(splitBlock.html, templates, budget);
        if (usedHeight > 0 && usedHeight + splitHeight > availableHeight) pushPage();
        appendBlock(splitBlock.html, splitHeight);
      }
      continue;
    }
    if (usedHeight > 0 && usedHeight + blockHeight > availableHeight) pushPage();
    appendBlock(block.html, blockHeight);
  }
  pages.push(currentPage);
  return pages;
}

function updatePageCounts(pages) {
  const total = pages.length;
  pages.forEach((page, index) => page.querySelectorAll('.page-footer').forEach((footer) => { footer.innerHTML = footer.innerHTML.replaceAll('{{pageCount}}', String(total)).replace(/Página\s+\d+\s+de\s+\d+/g, `Página ${index + 1} de ${total}`); }));
}

function renderPages(pages) {
  document.getElementById('document-root').replaceChildren(...pages);
}

async function main() {
  try {
    setStatus('Cargando datos...');
    const [rawBudget, templates] = await Promise.all([fetchJson('presupuesto.json'), loadTemplates()]);
    setStatus('Calculando...');
    const budget = calculateBudget(rawBudget);
    const blocks = buildBlocks(budget, templates);
    setStatus('Paginando...');
    const pages = paginateBlocks(blocks, templates, budget);
    updatePageCounts(pages);
    renderPages(pages);
    setStatus(`${pages.length} página(s) renderizada(s)`);
  } catch (error) {
    console.error(error);
    setStatus('Error');
    document.getElementById('document-root').innerHTML = `<div class="error-box"><strong>Error renderizando presupuesto</strong><br />${escapeHtml(error.message)}</div>`;
  }
}

main();
