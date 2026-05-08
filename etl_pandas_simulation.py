import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    # ==========================================
    # 1. EXTRAÇÃO E TRATAMENTO DE DADOS (ETL)
    # ==========================================
    df_base = pd.read_csv('telco_customer_churn.csv')
    
    np.random.seed(42)
    df_painel = df_base[np.random.rand(len(df_base)) <= 0.8][['customerID']].copy()
    df_painel['id_no_painel'] = df_painel['customerID']
    
    df_ativos = df_base[df_base['Churn'] == 'No'].copy()
    df_ativos['monthlycharges'] = df_ativos['MonthlyCharges'].astype(float)
    
    condicoes_tier = [
    (df_ativos['tenure'] >= 48) & (df_ativos['monthlycharges'] > 80),
    (df_ativos['tenure'] >= 24) & (df_ativos['monthlycharges'] > 60),
    (df_ativos['tenure'] >= 12) & (df_ativos['monthlycharges'] > 40)
    ]
    valores_tier = ['Platinum', 'Gold', 'Silver']
    
    df_ativos['tier'] = np.select(condicoes_tier, valores_tier, default='Bronze')
    
    media_grupo = df_ativos.groupby(['Contract', 'InternetService'])['monthlycharges'].transform('mean')
    
    df_ativos['pay_above_avg'] = np.where(df_ativos['monthlycharges'] > (media_grupo * 1.2), 1, 0)
    
    df_cruzado = df_ativos.merge(df_painel, on='customerID', how='left')
    
    condicao_alvo = (
        (df_cruzado['tier'].isin(['Platinum', 'Gold'])) &
        (df_cruzado['id_no_painel'].isna()) &  
        (df_cruzado['InternetService'] == 'Fiber optic') &
        (df_cruzado['TechSupport'] == 'No') &
        (df_cruzado['OnlineSecurity'] == 'No')
    )
    df_cruzado['target'] = np.where(condicao_alvo, 1, 0)

    df_cruzado['receita_risco_linha'] = np.where(df_cruzado['target'] == 1, df_cruzado['monthlycharges'], 0)

    df_agregado = df_cruzado.groupby(['tier', 'Contract']).agg(
        qtd_clientes_ativos=('customerID', 'nunique'),    
        qtd_clientes_criticos=('target', 'sum'),         
        receita_total=('monthlycharges', 'sum'), 
        receita_em_risco=('receita_risco_linha', 'sum')    
    ).reset_index()

    df_agregado['rank_de_risco'] = df_agregado['receita_em_risco'].rank(method='min', ascending=False).astype(int)
    df_agregado = df_agregado.sort_values('rank_de_risco').reset_index(drop=True)

    print("=== TABELA DE RESULTADOS ===")
    print(df_agregado.to_string())

    # ==========================================
    # 2. VISUALIZAÇÃO DE DADOS (DASHBOARD CORPORATIVO)
    # ==========================================
    print("\nGerando dashboard corporativo...")
    
    # Prepara os dados sumarizados para os gráficos
    df_tier = df_agregado.groupby('tier', as_index=False)[['receita_total', 'receita_em_risco']].sum()
    df_tier = df_tier.sort_values('receita_em_risco', ascending=False).reset_index(drop=True)
    
    df_contract = df_agregado.groupby('Contract', as_index=False)['receita_em_risco'].sum()
    df_contract = df_contract[df_contract['receita_em_risco'] > 0] 

    plt.style.use('default')
    sns.set_style("whitegrid")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'width_ratios': [2, 1]})
    

    cor_fundo = '#F8F9FA'
    fig.patch.set_facecolor(cor_fundo)
    ax1.set_facecolor(cor_fundo)
    ax2.set_facecolor(cor_fundo)

    fig.suptitle('Análise Risco de Faturamento', fontsize=18, fontweight='bold', color='#2C3E50', y=1.05)


    cor_azul_tim = '#0033A0' 
    sns.barplot(data=df_tier, x='tier', y='receita_em_risco', color=cor_azul_tim, ax=ax1)
    
    ax1.set_title('Receita em Risco por Categoria (Tier)', fontsize=14, pad=15, color='#34495E')
    ax1.set_xlabel('Categoria', fontsize=12, color='#7F8C8D')
    ax1.set_ylabel('Valor em Risco ($)', fontsize=12, color='#7F8C8D')
    
 
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_color('#BDC3C7')
    ax1.spines['bottom'].set_color('#BDC3C7')
    ax1.tick_params(colors='#34495E')


    for index, row in df_tier.iterrows():
        pct_risco = (row['receita_em_risco'] / row['receita_total']) * 100 if row['receita_total'] > 0 else 0
        
        valor_us = f"{row['receita_em_risco']:,.2f}"

        valor_br = valor_us.replace(',', 'X').replace('.', ',').replace('X', '.')
        
        texto = f"R$ {valor_br}\n({pct_risco:.1f}%)"
        
        ax1.text(index, row['receita_em_risco'] + (row['receita_em_risco'] * 0.02), 
                 texto, color='#2C3E50', ha="center", fontsize=11, fontweight='bold')


    if not df_contract.empty:
  
        cores_rosca = ['#0033A0', '#7F8C8D', '#BDC3C7'] 
        
        wedges, texts, autotexts = ax2.pie(df_contract['receita_em_risco'], labels=df_contract['Contract'], autopct='%1.1f%%', 
                startangle=90, colors=cores_rosca, textprops={'fontsize': 11, 'color': '#34495E', 'weight': 'bold'})
        

        for autotext in autotexts:
            autotext.set_color('black')

        circulo = plt.Circle((0,0), 0.70, fc=cor_fundo) 
        ax2.add_artist(circulo)
        ax2.set_title('Distribuição por Contrato', fontsize=14, pad=15, color='#34495E')
    else:
        ax2.text(0.5, 0.5, "Sem Risco Identificado", ha='center', va='center', fontsize=12, color='#7F8C8D')
        ax2.axis('off')


    plt.tight_layout()
    plt.savefig('dashboard_revenue_assurance.png', dpi=300, bbox_inches='tight')
    print("Sucesso! Imagem 'dashboard_revenue_assurance.png' salva na pasta.")
    

    plt.show()

if __name__ == '__main__':
    main()