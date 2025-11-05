// Este evento garante que o script só rode depois que a página (progresso.html)
// estiver totalmente carregada.
document.addEventListener("DOMContentLoaded", () => {

    // --- DADOS PARA OS GRÁFICOS ---
    const dadosStatus = {
        concluidas: 10,
        emProgresso: 5,
        paradas: 5
    };

    const dadosEvolucao = {
        // Meses (rótulos do eixo X)
        labels: ["Jun", "Jul", "Ago", "Set", "Out", "Nov"],
        // Dados (eixo Y)
        data: [1, 2, 4, 6, 8, 10] // Evolução de empresas concluídas
    };

    // --- 1. CONFIGURAÇÃO DO GRÁFICO DE PIZZA (STATUS GERAL) ---
    const ctxPizza = document.getElementById('graficoPizza');
    if (ctxPizza) {
        new Chart(ctxPizza, {
            type: 'doughnut', // Tipo "Rosquinha" (mais moderno que pizza)
            data: {
                labels: [
                    'Concluídas',
                    'Em Progresso',
                    'Paradas'
                ],
                datasets: [{
                    label: 'Status das Empresas',
                    data: [
                        dadosStatus.concluidas, 
                        dadosStatus.emProgresso, 
                        dadosStatus.paradas
                    ],
                    backgroundColor: [
                        '#107c10', // Verde (Concluídas - var(--success-color))
                        '#ffc600', // Amarelo (Em Progresso)
                        '#d83b01'  // Laranja (Paradas - var(--warning-color))
                    ],
                    borderColor: '#2d2d2d', // Cor de fundo do card (var(--card-color))
                    borderWidth: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false, // Permite que o gráfico preencha o container
                plugins: {
                    legend: {
                        position: 'bottom', // Põe a legenda embaixo
                        labels: {
                            color: '#f1f1f1' // Cor do texto (var(--text-primary))
                        }
                    }
                }
            }
        });
    } else {
        console.error("Elemento 'graficoPizza' não encontrado.");
    }

    // --- 2. CONFIGURAÇÃO DO GRÁFICO DE LINHA (EVOLUÇÃO) ---
    const ctxLinha = document.getElementById('graficoLinha');
    if (ctxLinha) {
        new Chart(ctxLinha, {
            type: 'line',
            data: {
                labels: dadosEvolucao.labels,
                datasets: [{
                    label: 'Empresas Concluídas',
                    data: dadosEvolucao.data,
                    fill: true,
                    backgroundColor: 'rgba(0, 120, 212, 0.2)', // Azul transparente (var(--accent-color))
                    borderColor: '#0078d4', // Azul sólido (var(--accent-color))
                    tension: 0.3 // Deixa a linha suave
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#b0b0b0' // Cor do texto eixo Y (var(--text-secondary))
                        },
                        grid: {
                            color: '#444' // Cor das linhas do grid (var(--border-color))
                        }
                    },
                    x: {
                        ticks: {
                            color: '#b0b0b0' // Cor do texto eixo X
                        },
                        grid: {
                            color: 'transparent' // Sem grid vertical
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false // Esconde a legenda (só temos 1 linha)
                    }
                }
            }
        });
    } else {
        console.error("Elemento 'graficoLinha' não encontrado.");
    }

    // NOTA: O 'app.js' (carregado no progresso.html) 
    // já cuida da lógica do menu hambúrguer. 
    // Este script cuida apenas dos gráficos.
});