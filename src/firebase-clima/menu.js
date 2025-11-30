// --- ARQUIVO: menu.js ---

document.addEventListener("DOMContentLoaded", function() {
    // 1. Cria o elemento HTML do menu
    const menuDiv = document.createElement('nav');
    menuDiv.className = 'sidebar-navegacao';
    
    // 2. Define o conteúdo (Os 3 ícones)
    // Usamos caminhos relativos. Se estiver em uma pasta, o navegador ajusta.
    menuDiv.innerHTML = `
        <ul class="lista-menu">
            <li>
                <a href="index.html" title="Início (Home)">
                    <span class="icone">🏠</span>
                    <span class="texto">Início</span>
                </a>
            </li>
            <li>
                <a href="criadores.html" title="Criadores">
                    <span class="icone">👥</span>
                    <span class="texto">Criadores</span>
                </a>
            </li>
            <li>
                <a href="graficos.html" title="Gráficos (Em breve)">
                    <span class="icone">📊</span>
                    <span class="texto">Gráficos</span>
                </a>
            </li>
        </ul>
    `;

    // 3. Adiciona o menu no começo do corpo da página (body)
    document.body.prepend(menuDiv);
});