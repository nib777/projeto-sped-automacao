document.addEventListener("DOMContentLoaded", () => {

    // --- Seletores ---
    const fileSpedInput = document.getElementById("file_sped");
    const fileLivroInput = document.getElementById("file_livro");
    const btnProcessar = document.getElementById("btn-processar-tudo");
    const btnText = document.getElementById("btn-text-processar");
    const loader = document.getElementById("loader-processar");
    const statusTotais = document.getElementById("status-message-totais");
    const cardDetalhamento = document.getElementById("card-detalhamento");
    const statusDetalhamento = document.getElementById("status-detalhamento");
    const blocoETableBody = document.getElementById("bloco-e-table-body"); 
    const detalhamentoTableBody = document.getElementById("detalhamento-table-body");
    const cardAlertas = document.getElementById("card-alertas");
    const statusAlertas = document.getElementById("status-alertas");
    const listaAlertas = document.getElementById("lista-alertas-codigos");

    const cardDetalheE116 = document.getElementById("card-detalhe-e116");
    const statusDetalheE116 = document.getElementById("status-detalhe-e116");
    const spedE116Soma = document.getElementById("sped-e116-soma");
    const livroInfCompSoma = document.getElementById("livro-infcomp-soma");


    // --- FUNÇÃO DE FORMATAR NÚMEROS (Original) ---
    function formatarNumero(numStr) {
        if (!numStr || typeof numStr !== 'string' || numStr === "Não lido" || numStr === "--") {
            return "--"; 
        }
        let valor = parseFloat(numStr.replace(/\./g, "").replace(",", "."));
        if (isNaN(valor)) {
            return numStr; 
        }
        return valor.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // --- FUNÇÃO PARA FORMATAR NOSSOS NOVOS VALORES (Decimal) ---
    function formatarValorDecimal(numStr) {
        if (!numStr && numStr !== 0) {
            return "--";
        }
        let valor = parseFloat(String(numStr)); 
        if (isNaN(valor)) {
            return String(numStr);
        }
        return valor.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // Para atualizar os mini status
    function atualizarMiniStatus(elementId, status, nome) {
        const el = document.getElementById(elementId);
        if (!el) return;
        el.classList.remove("aguardando", "ok", "divergente");
        if (status === "OK") {
            el.textContent = `${nome} OK`;
            el.classList.add("ok");
        } else if (status === "Divergente") {
            el.textContent = `${nome} Divergente`;
            el.classList.add("divergente");
        } else {
            // Se status for indefinido ou "Falha"
            el.textContent = `${nome} Falha`;
            el.classList.add("divergente");
        }
    }

    // --- Função Soma E116 ---
    function somarValoresE116(blocoETexto) {
        if (!blocoETexto || typeof blocoETexto !== 'string') {
            return 0.0;
        }
        let totalSoma = 0.0;
        const linhas = blocoETexto.split('\n');
        linhas.forEach(linha => {
            if (linha.startsWith('|E116|')) {
                const campos = linha.split('|');
                if (campos.length > 3) {
                    const valorStr = campos[3];
                    if (valorStr) {
                        try {
                            const valorLimpo = valorStr.replace(/\./g, "").replace(",", ".");
                            const valorFloat = parseFloat(valorLimpo);
                            if (!isNaN(valorFloat)) {
                                totalSoma += valorFloat;
                            }
                        } catch (e) {
                            console.error(`Erro ao somar valor E116: ${valorStr}`, e);
                        }
                    }
                }
            }
        });
        return totalSoma;
    }


    // --- "Ouvinte" do Botão Mestre ---
    btnProcessar.addEventListener("click", async () => {
        
        if (!fileSpedInput.files[0] || !fileLivroInput.files[0]) {
            statusTotais.textContent = "ERRO: Você precisa selecionar o arquivo SPED.txt E o Livro.pdf para conciliar.";
            return;
        }

        statusTotais.textContent = "Iniciando o robô (Wall-E)... Isso vai demorar vários minutos. O PVA será aberto na sua tela.";
        btnProcessar.disabled = true;
        btnText.textContent = "Processando...";
        loader.classList.remove("hidden");
        limparResultados(); 

        const formData = new FormData();
        formData.append("file_sped", fileSpedInput.files[0]);
        formData.append("file_livro", fileLivroInput.files[0]);
        
        try {
            const response = await fetch("/upload-e-processar/", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Erro no Processamento: ${extractError(errorText)}`);
            }
            
            const resultados = await response.json();
            
            statusTotais.textContent = "Análise CONCLUÍDA! Verificando resultados...";
            
            preencherResultadosTotais(resultados); 
            preencherBlocoE(resultados.bloco_e_texto);
            preencherAnaliseDetalhamento(resultados.detalhamento_codigos);
            preencherAlertasCodigos(resultados.codigos_ausentes_livro);

            const soma_pdf_inf_comp = resultados.soma_livro_inf_comp || 0.0;
            const soma_sped_e116 = somarValoresE116(resultados.bloco_e_texto);
            preencherSomaDetalhada(soma_sped_e116, soma_pdf_inf_comp);

        } catch (error) {
            console.error("Erro:", error);
            statusTotais.textContent = `ERRO: ${error.message}`;
            if(cardDetalhamento) cardDetalhamento.classList.add("divergente");
            if(statusDetalhamento) statusDetalhamento.textContent = "Falha na Análise";
            if(cardAlertas) cardAlertas.classList.add("divergente");
            if(statusAlertas) statusAlertas.textContent = "Falha na Análise";
        } finally {
            btnProcessar.disabled = false;
            btnText.textContent = "Processar Análise Completa";
            loader.classList.add("hidden");
        }
    });
    
    function extractError(errorText) {
        try {
            const errorJson = JSON.parse(errorText);
            return errorJson.detail || "Erro no servidor (JSON).";
        } catch (e) {
            return errorText || "Erro desconhecido no servidor.";
        }
    }

    
    // --- [FUNÇÃO ATUALIZADA] ---
    function preencherResultadosTotais(data) {
        if (!data || !data.entradas) { 
            console.error("JSON 'entradas' está vazio.");
            return; 
        }
        
        // --- JANELA 1: ENTRADAS ---
        const cardE = document.getElementById("card-entradas");
        const statusE = document.getElementById("resultado-entradas");
        cardE.classList.remove("aguardando");
        
        // Pega os objetos (garante que não sejam nulos)
        const spedE = data.entradas.sped || {};
        const livroE = data.entradas.livro || {};
        const statusE_detalhado = data.entradas.status_detalhado || {};

        // Preenche os valores
        document.getElementById("sped-e-total").textContent = formatarNumero(spedE.total_operacao);
        document.getElementById("sped-e-bc").textContent = formatarNumero(spedE.base_de_calculo_icms);
        document.getElementById("sped-e-icms").textContent = formatarNumero(spedE.total_icms);
        
        document.getElementById("livro-e-total").textContent = formatarNumero(livroE.total_operacao);
        document.getElementById("livro-e-bc").textContent = formatarNumero(livroE.base_de_calculo_icms);
        document.getElementById("livro-e-icms").textContent = formatarNumero(livroE.total_icms);

        // Preenche o status geral
        if (data.entradas.status === "OK") {
            statusE.textContent = "Valores idênticos";
            statusE.className = "status-box ok";
            cardE.classList.add("ok");
        } else {
            statusE.textContent = "Valores divergentes";
            statusE.className = "status-box divergente";
            cardE.classList.add("divergente");
        }
        
        // Preenche os status individuais
        atualizarMiniStatus("status-e-total", statusE_detalhado.total_operacao, "Total Op.");
        atualizarMiniStatus("status-e-bc", statusE_detalhado.base_de_calculo_icms, "Base ICMS");
        atualizarMiniStatus("status-e-icms", statusE_detalhado.total_icms, "Total ICMS");

        
        // --- JANELA 2: SAÍDAS ---
        const cardS = document.getElementById("card-saidas");
        const statusS = document.getElementById("resultado-saidas");
        cardS.classList.remove("aguardando");

        const spedS = data.saidas.sped || {};
        const livroS = data.saidas.livro || {};
        const statusS_detalhado = data.saidas.status_detalhado || {};

        // Preenche os valores
        document.getElementById("sped-s-total").textContent = formatarNumero(spedS.total_operacao);
        document.getElementById("sped-s-bc").textContent = formatarNumero(spedS.base_de_calculo_icms);
        document.getElementById("sped-s-icms").textContent = formatarNumero(spedS.total_icms);
        
        document.getElementById("livro-s-total").textContent = formatarNumero(livroS.total_operacao);
        document.getElementById("livro-s-bc").textContent = formatarNumero(livroS.base_de_calculo_icms);
        document.getElementById("livro-s-icms").textContent = formatarNumero(livroS.total_icms);

        // Preenche o status geral
        if (data.saidas.status === "OK") {
            statusS.textContent = "Valores idênticos";
            statusS.className = "status-box ok";
            cardS.classList.add("ok");
        } else {
            statusS.textContent = "Valores divergentes";
            statusS.className = "status-box divergente";
            cardS.classList.add("divergente");
        }

        // Preenche os status individuais
        atualizarMiniStatus("status-s-total", statusS_detalhado.total_operacao, "Total Op.");
        atualizarMiniStatus("status-s-bc", statusS_detalhado.base_de_calculo_icms, "Base ICMS");
        atualizarMiniStatus("status-s-icms", statusS_detalhado.total_icms, "Total ICMS");


        // --- JANELA 3: APURAÇÃO ---
        const cardA = document.getElementById("card-apuracao");
        cardA.classList.remove("aguardando");
        
        document.getElementById("sped-a1").textContent = formatarNumero(data.apuracao.sped_recolher);
        document.getElementById("sped-a2").textContent = formatarNumero(data.apuracao.sped_saldo_credor);
        
        const livroValores = data.apuracao.livro_valores || {};
        document.getElementById("livro-a1").textContent = formatarNumero(livroValores["013"]);
        document.getElementById("livro-a2").textContent = formatarNumero(livroValores["014"]);
        
        atualizarMiniStatus("resultado-apuracao-1", data.apuracao.status_recolher, "Cód. 013");
        atualizarMiniStatus("resultado-apuracao-2", data.apuracao.status_saldo_credor, "Cód. 014");
        
        if (data.apuracao.status_recolher === "OK" && data.apuracao.status_saldo_credor === "OK") {
            cardA.classList.remove("divergente");
            cardA.classList.add("ok");
        } else {
            cardA.classList.add("divergente");
        }
    }

    // --- Função Soma E116 ---
    function preencherSomaDetalhada(soma_sped, soma_pdf) {
        if (!cardDetalheE116) return;

        const spedFormatado = formatarValorDecimal(soma_sped.toString());
        const livroFormatado = formatarValorDecimal(soma_pdf.toString());

        spedE116Soma.textContent = `R$ ${spedFormatado}`;
        livroInfCompSoma.textContent = `R$ ${livroFormatado}`;

        cardDetalheE116.classList.remove("aguardando", "ok", "divergente");

        if (Math.abs(soma_sped - soma_pdf) < 0.01) {
            statusDetalheE116.textContent = "Valores idênticos";
            statusDetalheE116.className = "status-box ok";
            cardDetalheE116.classList.add("ok");
        } else {
            statusDetalheE116.textContent = "Valores divergentes";
            statusDetalheE116.className = "status-box divergente";
            cardDetalheE116.classList.add("divergente");
        }
    }

    // --- (Função preencherAlertasCodigos) ---
    function preencherAlertasCodigos(codigos_ausentes) {
        if (!cardAlertas || !statusAlertas || !listaAlertas) return;
        cardAlertas.classList.remove("aguardando", "ok", "divergente");
        listaAlertas.innerHTML = ""; 
        if (codigos_ausentes && codigos_ausentes.length > 0) {
            cardAlertas.classList.add("divergente");
            statusAlertas.textContent = `${codigos_ausentes.length} Alerta(s) Encontrado(s)`;
            statusAlertas.className = "status-box divergente";
            codigos_ausentes.forEach(codigo => {
                const li = document.createElement("li");
                li.textContent = `O código ${codigo} (do SPED E111) não foi encontrado no Livro Fiscal.`;
                listaAlertas.appendChild(li);
            });
        } else if (codigos_ausentes && codigos_ausentes.length === 0) {
            cardAlertas.classList.add("ok");
            statusAlertas.textContent = "Tudo Certo";
            statusAlertas.className = "status-box ok";
            listaAlertas.innerHTML = "<li>Todos os códigos de ajuste E111 do SPED foram encontrados no Livro Fiscal.</li>";
        } else {
            cardAlertas.classList.add("divergente");
            statusAlertas.textContent = "Falha na Verificação";
            statusAlertas.className = "status-box divergente";
            listaAlertas.innerHTML = "<li>Não foi possível verificar os códigos E111. (Erro no script 'ler_pdf.py')</li>";
        }
    }

    // --- (Função preencherBlocoE) ---
    function preencherBlocoE(textoBlocoE) {
        if (!blocoETableBody) return; 
        blocoETableBody.innerHTML = ""; 
        if (textoBlocoE && textoBlocoE !== "Bloco E não encontrado ou vazio.") {
            const linhas = textoBlocoE.split('\n');
            let htmlFinalTabela = ""; 
            const regexValor = /^\d[\d\.]*,\d{2}$/; 
            const regexCodigoAjuste = /^[A-Z]{2}\d{5,12}$/;
            linhas.forEach(linha => {
                if (!linha.trim()) return; 
                let classeLinha = ''; 
                if (linha.startsWith('|E110|')) classeLinha = 'reg-e110';
                else if (linha.startsWith('|E111|')) classeLinha = 'reg-e111';
                else if (linha.startsWith('|E116|')) classeLinha = 'reg-e116';
                else if (linha.startsWith('|E001|') || linha.startsWith('|E990|')) classeLinha = 'reg-e001';
                htmlFinalTabela += `<tr class="${classeLinha}">`;
                const campos = linha.split('|');
                for (let i = 1; i < campos.length - 1; i++) {
                    const campo = campos[i];
                    let classeCampo = 'campo-default'; 
                    let valorFormatado = campo;
                    if (regexValor.test(campo)) {
                        classeCampo = 'valor-monetario';
                        valorFormatado = 'R$ ' + formatarNumero(campo); 
                    }
                    else if (regexCodigoAjuste.test(campo)) {
                        classeCampo = 'codigo-ajuste';
                    }
                    htmlFinalTabela += `<td class="${classeCampo}">${valorFormatado}</td>`;
                }
                htmlFinalTabela += `</tr>`;
            });
            blocoETableBody.innerHTML = htmlFinalTabela;
            if(statusDetalhamento) statusDetalhamento.textContent = "Pronto para análise manual";
            if(cardDetalhamento) cardDetalhamento.classList.add("ok");
        } else {
            blocoETableBody.innerHTML = '<tr><td class="status-divergente">ERRO: O Bloco E não pôde ser extraído do arquivo SPED.txt.</td></tr>';
            if(statusDetalhamento) statusDetalhamento.textContent = "Falha ao ler Bloco E";
            if(cardDetalhamento) cardDetalhamento.classList.add("divergente");
        }
    }

    // --- (Função preencherAnaliseDetalhamento) ---
    function preencherAnaliseDetalhamento(codigos) {
        if (!detalhamentoTableBody) return; 
        detalhamentoTableBody.innerHTML = ""; 
        if (codigos && Object.keys(codigos).length > 0) {
            detalhamentoTableBody.innerHTML = `
                <tr>
                    <th>Código de Ajuste</th>
                    <th>Valor Total no Livro (PDF)</th>
                </tr>
            `;
            Object.keys(codigos).sort().forEach(codigo => {
                const valorFormatado = formatarValorDecimal(codigos[codigo]);
                const row = `
                    <tr>
                        <td>${codigo}</td>
                        <td>R$ ${valorFormatado}</td>
                    </tr>
                `;
                detalhamentoTableBody.innerHTML += row;
            });
        } else {
            detalhamentoTableBody.innerHTML = `<tr><td colspan="2">Nenhum código de detalhamento (PA, MG, etc.) foi encontrado no Livro PDF.</td></tr>`;
            if(statusDetalhamento) statusDetalhamento.textContent = "Códigos não encontrados no PDF";
            if(cardDetalhamento) cardDetalhamento.classList.add("divergente");
        }
    }
    
    // --- [FUNÇÃO ATUALIZADA] ---
    function limparResultados() {
        // Limpa Totais
        const cards = document.querySelectorAll('.card-resultado');
        cards.forEach(card => {
            card.classList.remove('ok', 'divergente');
            card.classList.add('aguardando');
        });
        const statusBoxes = document.querySelectorAll('.status-box');
        statusBoxes.forEach(box => {
            box.textContent = "Aguardando...";
            box.className = "status-box aguardando";
        });

        // [MUDANÇA] Limpa os novos campos de Entradas
        document.getElementById("sped-e-total").textContent = "--";
        document.getElementById("sped-e-bc").textContent = "--";
        document.getElementById("sped-e-icms").textContent = "--";
        document.getElementById("livro-e-total").textContent = "--";
        document.getElementById("livro-e-bc").textContent = "--";
        document.getElementById("livro-e-icms").textContent = "--";
        
        // [MUDANÇA] Limpa os novos campos de Saídas
        document.getElementById("sped-s-total").textContent = "--";
        document.getElementById("sped-s-bc").textContent = "--";
        document.getElementById("sped-s-icms").textContent = "--";
        document.getElementById("livro-s-total").textContent = "--";
        document.getElementById("livro-s-bc").textContent = "--";
        document.getElementById("livro-s-icms").textContent = "--";

        // Limpa Apuração
        document.getElementById("sped-a1").textContent = "--";
        document.getElementById("sped-a2").textContent = "--";
        document.getElementById("livro-a1").textContent = "--";
        document.getElementById("livro-a2").textContent = "--";
        
        // Limpa TODOS os mini status
        const miniBoxes = document.querySelectorAll('.status-box-mini');
        miniBoxes.forEach(box => {
            box.textContent = "Aguardando...";
            box.className = "status-box-mini aguardando";
        });
        
        // Limpa Detalhamento
        if(statusDetalhamento) statusDetalhamento.textContent = "Aguardando...";
        if(blocoETableBody) blocoETableBody.innerHTML = "";
        if(detalhamentoTableBody) detalhamentoTableBody.innerHTML = "";

        // Limpa Alertas
        if(statusAlertas) statusAlertas.textContent = "Aguardando...";
        if(listaAlertas) listaAlertas.innerHTML = "";

        // Limpa o card E116
        if(cardDetalheE116) {
            cardDetalheE116.classList.remove('ok', 'divergente');
            cardDetalheE116.classList.add('aguardando');
        }
        if(statusDetalheE116) {
            statusDetalheE116.textContent = "Aguardando...";
            statusDetalheE116.className = "status-box aguardando";
        }
        if(spedE116Soma) spedE116Soma.textContent = "--";
        if(livroInfCompSoma) livroInfCompSoma.textContent = "--";

        // Reseta os filtros
        const filtroBtns = document.querySelectorAll(".filtro-btn");
        filtroBtns.forEach(btn => {
            btn.classList.remove("active");
            if(btn.dataset.filtro === "todos") {
                btn.classList.add("active");
            }
        });
    }

    // --- Filtros e Menu (Sem Mudança) ---
    const filtroBtns = document.querySelectorAll(".filtro-btn");
    filtroBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            filtroBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const filtro = btn.dataset.filtro; 
            const linhas = blocoETableBody.querySelectorAll("tr");
            linhas.forEach(linha => {
                if (filtro === "todos" || linha.classList.contains(filtro)) {
                    linha.style.display = ""; 
                } else {
                    linha.style.display = "none"; 
                }
            });
        });
    });

    const menuToggleBtn = document.getElementById("menu-toggle-btn");
    const sidebar = document.querySelector(".sidebar");
    const contentWrapper = document.querySelector(".content-wrapper");
    menuToggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        contentWrapper.classList.toggle("shifted");
    });
});