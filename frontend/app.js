document.addEventListener("DOMContentLoaded", () => {

    // --- Seletores dos Inputs ---
    const fileSpedInput = document.getElementById("file_sped");
    const fileLivroInput = document.getElementById("file_livro");

    // --- Seletores do Botão Único ---
    const btnProcessar = document.getElementById("btn-processar-tudo");
    const btnText = document.getElementById("btn-text-processar");
    const loader = document.getElementById("loader-processar");
    
    // --- Seletores das Mensagens de Status ---
    const statusTotais = document.getElementById("status-message-totais");
    const statusExcel = document.getElementById("status-message-excel"); // (Nós removemos, mas deixamos o seletor)


    // --- FUNÇÃO DE FORMATAR NÚMEROS (SEU PEDIDO) ---
    function formatarNumero(numStr) {
        if (!numStr || typeof numStr !== 'string' || numStr === "Não lido" || numStr === "--") {
            return "--"; // Retorna "--" se for nulo ou "Não lido"
        }
        
        // 1. Limpa (remove pontos, troca vírgula) e converte para número
        let valor = parseFloat(numStr.replace(/\./g, "").replace(",", "."));
        
        if (isNaN(valor)) {
            return numStr; // Retorna o texto original se não for um número
        }
        
        // 2. Formata de volta para o padrão brasileiro (com pontos e vírgula)
        return valor.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // --- "Ouvinte" do Botão Mestre ---
    btnProcessar.addEventListener("click", async () => {
        
        // Validação
        if (!fileSpedInput.files[0] || !fileLivroInput.files[0]) {
            statusTotais.textContent = "ERRO: Você precisa selecionar o arquivo SPED.txt E o Livro.pdf para conciliar.";
            return;
        }

        // --- 1. Mostrar que está carregando ---
        statusTotais.textContent = "Iniciando o robô (Wall-E)... Isso vai demorar vários minutos. O PVA será aberto na sua tela.";
        if (statusExcel) statusExcel.textContent = ""; // Limpa a outra mensagem
        btnProcessar.disabled = true;
        btnText.textContent = "Processando...";
        loader.classList.remove("hidden");
        limparResultados(); // Limpa os cards de resultado

        // --- 2. Preparar os dados ---
        const formData = new FormData();
        formData.append("file_sped", fileSpedInput.files[0]);
        formData.append("file_livro", fileLivroInput.files[0]);
        
        // --- 3. Chamar o ÚNICO Endpoint Mestre ---
        try {
            const response = await fetch("/processar-tudo/", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Erro no Processamento: ${extractError(errorText)}`);
            }
            
            const resultados = await response.json();
            
            // --- 4. PREENCHER TUDO ---
            statusTotais.textContent = "Etapa 1/2: Conciliação de Totais CONCLUÍDA!";
            preencherResultadosTotais(resultados.conciliacao_totais);
            
            // (Esta mensagem de status do excel foi removida do HTML, então
            //  vamos logar no status principal)
            statusTotais.textContent = "Etapa 2/2: Conciliação de Detalhes CONCLUÍDA!";
            preencherResultadosDetalhes(resultados.conciliacao_detalhes);

        } catch (error) {
            console.error("Erro:", error);
            statusTotais.textContent = `ERRO: ${error.message}`;
        } finally {
            // Roda sempre (dando certo ou errado)
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

    
    // --- FUNÇÕES DE PREENCHER O DASHBOARD ---
    
    function preencherResultadosTotais(data) {
        if (!data) { 
            console.error("JSON 'conciliacao_totais' está vazio.");
            return; 
        }
        
        // --- JANELA 1: ENTRADAS ---
        const cardE = document.getElementById("card-entradas");
        const statusE = document.getElementById("resultado-entradas");
        document.getElementById("sped-e").textContent = formatarNumero(data.entradas.sped);
        document.getElementById("livro-e").textContent = formatarNumero(data.entradas.livro);
        
        cardE.classList.remove("aguardando");
        if (data.entradas.status === "OK") {
            statusE.textContent = "Valores idênticos";
            statusE.className = "status-box ok";
            cardE.classList.add("ok");
        } else {
            statusE.textContent = "Valores divergentes";
            statusE.className = "status-box divergente";
            cardE.classList.add("divergente");
        }
        
        // --- JANELA 2: SAÍDAS ---
        const cardS = document.getElementById("card-saidas");
        const statusS = document.getElementById("resultado-saidas");
        document.getElementById("sped-s").textContent = formatarNumero(data.saidas.sped);
        document.getElementById("livro-s").textContent = formatarNumero(data.saidas.livro);

        cardS.classList.remove("aguardando");
        if (data.saidas.status === "OK") {
            statusS.textContent = "Valores idênticos";
            statusS.className = "status-box ok";
            cardS.classList.add("ok");
        } else {
            statusS.textContent = "Valores divergentes";
            statusS.className = "status-box divergente";
            cardS.classList.add("divergente");
        }

        // --- JANELA 3: APURAÇÃO (E116) ---
        const cardA = document.getElementById("card-apuracao");
        cardA.classList.remove("aguardando");
        
        document.getElementById("sped-a1").textContent = formatarNumero(data.apuracao.sped_recolher);
        document.getElementById("sped-a2").textContent = formatarNumero(data.apuracao.sped_extra);
        document.getElementById("livro-a1").textContent = formatarNumero(data.apuracao.livro_valores[0]);
        document.getElementById("livro-a2").textContent = formatarNumero(data.apuracao.livro_valores[1]);
        
        const cardA1 = document.getElementById("resultado-apuracao-1");
        if (data.apuracao.status_recolher === "OK") {
            cardA1.textContent = "Valor 1 idêntico";
            cardA1.className = "status-box-mini ok";
            cardA.classList.add("ok");
        } else {
            cardA1.textContent = "Valor 1 divergente";
            cardA1.className = "status-box-mini divergente";
            cardA.classList.add("divergente");
        }
        
        const cardA2 = document.getElementById("resultado-apuracao-2");
        if (data.apuracao.status_extra === "OK") {
            cardA2.textContent = "Valor 2 idêntico";
            cardA2.className = "status-box-mini ok";
        } else {
            cardA2.textContent = "Valor 2 divergente";
            cardA2.className = "status-box-mini divergente";
            cardA.classList.add("divergente");
        }
        
        if (data.apuracao.status_recolher === "OK" && data.apuracao.status_extra === "OK") {
            cardA.classList.remove("divergente");
            cardA.classList.add("ok");
        }
    }

    // --- NOVA FUNÇÃO PARA PREENCHER OS DETALHES (E110) ---
    function preencherResultadosDetalhes(data) {
        if (!data || !data.conciliacao_E110) { 
            console.error("JSON 'conciliacao_detalhes' está vazio ou não tem E110.");
            return; 
        }
        
        const cardE110 = document.getElementById("card-e110");
        const tableBody = document.getElementById("e110-table");
        const btnToggle = document.getElementById("btn-toggle-e110");
        const detailsBody = document.getElementById("e110-details");
        
        tableBody.innerHTML = ""; // Limpa a tabela antiga
        cardE110.classList.remove("aguardando");

        if (data.conciliacao_E110.length > 0) {
            
            let divergencias = 0;
            
            // Cria o Cabeçalho da Tabela
            tableBody.innerHTML = `
                <tr>
                    <th>Campo (E110)</th>
                    <th>Valor SPED (.txt)</th>
                    <th>Valor Livro (.pdf)</th>
                    <th>Status</th>
                </tr>
            `;

            // Preenche a tabela com os dados
            data.conciliacao_E110.forEach(item => {
                const statusClass = (item.status === "[OK]") ? "status-ok" : "status-divergente";
                if(item.status !== "[OK]") divergencias++;
                
                const row = `
                    <tr>
                        <td>${item.campo}</td>
                        <td>${item.valor_sped}</td>
                        <td>${item.valor_livro}</td>
                        <td class="${statusClass}">${item.status}</td>
                    </tr>
                `;
                tableBody.innerHTML += row;
            });
            
            // Define a cor do card
            if (divergencias === 0) {
                cardE110.classList.add("ok");
                btnToggle.textContent = "Exibir Detalhes (OK)";
            } else {
                cardE110.classList.add("divergente");
                btnToggle.textContent = `Exibir Detalhes (${divergencias} Diverg.)`;
            }
            
            // Ativa o botão "sanfona"
            btnToggle.disabled = false;
            
        } else {
            cardE110.classList.add("divergente");
            btnToggle.textContent = "Falha ao Ler E110";
            btnToggle.disabled = true;
            detailsBody.innerHTML = "<p>Não foi possível extrair os dados de conciliação do E110.</p>";
        }
    }
    
    // --- LÓGICA DO BOTÃO "SANFONA" ---
    const btnToggleE110 = document.getElementById("btn-toggle-e110");
    btnToggleE110.addEventListener("click", () => {
        const detailsBody = document.getElementById("e110-details");
        detailsBody.classList.toggle("open");
        
        if (detailsBody.classList.contains("open")) {
            btnToggleE110.textContent = "Ocultar Detalhes";
        } else {
            // Retorna ao texto original
            const card = document.getElementById("card-e110");
            if (card.classList.contains("ok")) {
                btnToggleE110.textContent = "Exibir Detalhes (OK)";
            } else {
                const divCount = document.querySelectorAll('#e110-table .status-divergente').length;
                btnToggleE110.textContent = divCount > 0 ? `Exibir Detalhes (${divCount} Diverg.)` : "Exibir Detalhes";
            }
        }
    });

    function limparResultados() {
        // Limpa os cards de Totais
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
        
        document.getElementById("sped-e").textContent = "--";
        document.getElementById("livro-e").textContent = "--";
        document.getElementById("sped-s").textContent = "--";
        document.getElementById("livro-s").textContent = "--";
        
        document.getElementById("sped-a1").textContent = "--";
        document.getElementById("sped-a2").textContent = "--";
        document.getElementById("livro-a1").textContent = "--";
        document.getElementById("livro-a2").textContent = "--";
        
        const miniBoxes = document.querySelectorAll('.status-box-mini');
        miniBoxes.forEach(box => {
            box.textContent = "Aguardando...";
            box.className = "status-box-mini aguardando";
        });
        
        // Limpa os novos cards de Detalhes
        document.getElementById("e110-table").innerHTML = "";
        document.getElementById("e110-details").classList.remove("open");
        document.getElementById("btn-toggle-e110").textContent = "Exibir Detalhes";
        document.getElementById("btn-toggle-e110").disabled = true;
    }
});