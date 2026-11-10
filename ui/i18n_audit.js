// Проверка перевода (для разработки): открыть ui/index.html?mock&audit — прогоняет все экраны на английском
// и выводит в консоль строки, которые остались по-русски. В приложение не встраивается.
window.i18nAudit = async function(){
  const W = ms => new Promise(r => setTimeout(r, ms));
  const left = new Set();
  const scan = () => {
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    let n;
    while ((n = w.nextNode())){
      if (n.nodeType === 3){
        const p = n.parentElement;
        if (!p || p.closest(NOTR) || p.closest(".hidden")) continue;
        if (CYR.test(n.nodeValue)) left.add(n.nodeValue.trim());
      } else for (const a of ["placeholder", "title"]) if (n.hasAttribute(a) && CYR.test(n.getAttribute(a))) left.add("@" + a + ": " + n.getAttribute(a));
    }
  };
  const step = async (fn, ms=700) => { try{ await fn(); }catch(e){ left.add("!! " + e.message); } await W(ms); scan(); };
  const clear = () => { $("#layer").innerHTML = ""; $("#upd").classList.add("hidden"); $$(".toast").forEach(t => t.remove()); const m = $("#accMenu"); if (m) m.remove(); };
  switchLang("en");
  await step(() => showLogin("Ключ не подошёл: FunPay не узнал аккаунт. Проверьте golden_key."));
  await step(() => doLogin("x".repeat(32), true), 2200);
  await step(() => { clear(); setView("lots"); });
  await step(() => { S.picked.add(101); updateBulk(); });
  await step(() => $("[data-bulk=price]").click()); clear();
  await step(() => $("[data-bulk=text]").click()); clear();
  await step(() => $("#raiseBtn").click()); clear();
  await step(() => $("#moreBtn").click()); clear();
  await step(() => openEditor(1355, 101), 1200);
  await step(() => $("[data-ai=fill]").click());
  await step(() => $("[data-ai=tpl]").click(), 900); clear();
  await step(() => duplicateLot(1355, 101), 1300); clear();
  await step(() => $("#newBtn").click(), 900); clear();
  await step(() => { deleteLots([{ node: 1355, id: 101, title: "Лот" }]); }, 400); clear();  // окно ждёт ответа — не ждём
  await step(() => setView("orders"), 1300);
  await step(() => askRentalTime("ORDER001")); clear();
  await step(() => openOrder("ORDER003"), 1000); clear();
  await step(() => openChatById(77, "buyer1"), 1300);
  await step(() => setView("fin"), 1300);
  await step(() => openWithdraw("usd"), 600);
  await step(async () => { $("#wAll").click(); await W(500); $("#wNext").click(); }, 1000); clear();
  await step(() => { setView("stats"); renderStatsShell(); }, 1300);
  await step(() => { S.statTab = "comp"; renderStatsShell(); }, 1300);
  await step(() => openSettings(), 900); clear();
  await step(() => checkUpdate(true), 900);
  await step(() => $("#acc").click(), 700); clear();
  await step(() => { toast("Сохранено"); toast("Нет связи с FunPay: timeout", true); }, 200);
  const list = [...left].filter(Boolean).sort();
  console.log("I18N AUDIT: " + list.length + " untranslated\n" + list.join("\n"));
  window.__audit = list;
  return list;
};
