
import streamlit as st
import json
import pandas as pd
from datetime import datetime
from src.database import get_db_client
from src.sidebar import render_sidebar
from src.s3_utils import get_article_by_id, get_article_content
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import io
import base64

st.set_page_config(page_title="Conformidade do Fundo", layout="wide")

# Render the custom sidebar
render_sidebar()

st.title("📊 Conformidade do Fundo")
st.write("Análise de conformidade regulatória dos artigos do fundo com as regras CVM175")

st.divider()

# Function to fetch compliance data from database
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_compliance_data():
    """Fetch compliance analysis data from the database"""
    try:
        db_client = get_db_client()
        if db_client is None:
            st.warning("Database connection not available. Please check your configuration.")
            return []
            
        # Query all compliance analyses
        query = """
        SELECT 
            article_id,
            article_number,
            chapter,
            section,
            is_compliant,
            individual_rule_analysis,
            summary_document,
            processed_at
        FROM compliance_analyses 
        ORDER BY processed_at DESC
        """
        
        results = db_client.query(query)
        return results
    except Exception as e:
        st.error(f"Erro ao buscar dados: {str(e)}")
        return []

# Function to parse individual rule analysis JSON
def parse_individual_analysis(json_str):
    """Parse the individual rule analysis JSON string"""
    try:
        if json_str and json_str != "{}" and json_str != "[]":
            return json.loads(json_str)
        return []
    except json.JSONDecodeError:
        return []

# Function to generate PDF report
def generate_compliance_pdf(compliance_data, selected_article=None):
    """Generate a comprehensive PDF report of compliance analysis"""
    
    # Create a BytesIO buffer to hold the PDF
    buffer = io.BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, 
                           topMargin=72, bottomMargin=18)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=8,
        textColor=colors.darkgreen
    )
    
    # Build the PDF content
    story = []
    
    # Title
    story.append(Paragraph("Relatório de Conformidade Regulatória", title_style))
    story.append(Paragraph("Análise CVM175 - Fundo de Investimento", styles['Heading2']))
    story.append(Spacer(1, 20))
    
    # Executive Summary
    story.append(Paragraph("Resumo Executivo", heading_style))
    
    total_articles = len(compliance_data)
    compliant_articles = sum(1 for item in compliance_data if item.get('is_compliant', False))
    non_compliant_articles = total_articles - compliant_articles
    compliance_rate = (compliant_articles / total_articles * 100) if total_articles > 0 else 0
    
    summary_text = f"""
    <b>Total de Artigos Analisados:</b> {total_articles}<br/>
    <b>Artigos Conformes:</b> {compliant_articles}<br/>
    <b>Artigos Não Conformes:</b> {non_compliant_articles}<br/>
    <b>Taxa de Conformidade Geral:</b> {compliance_rate:.1f}%
    """
    
    story.append(Paragraph(summary_text, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Add a note about the detailed analysis
    story.append(Paragraph("Análise Detalhada por Artigo", heading_style))
    story.append(Paragraph("A seguir, apresentamos a análise detalhada de cada artigo, incluindo o status de conformidade, análise individual das regras e citações regulatórias relevantes.", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Detailed analysis for each article
    for item in compliance_data:
        story.append(Paragraph(f"Artigo {item.get('article_number', 'N/A')} - {item.get('section', 'N/A')}", heading_style))
        
        # Article status
        status = 'CONFORME' if item.get('is_compliant', False) else 'NÃO CONFORME'
        status_color = colors.green if item.get('is_compliant', False) else colors.red
        story.append(Paragraph(f"<b>Status:</b> <font color='{status_color}'>{status}</font>", styles['Normal']))
        story.append(Spacer(1, 10))
        
        # Summary document generation is disabled for now
        # if item.get('summary_document'):
        #     story.append(Paragraph("Resumo da Análise", subheading_style))
        #     story.append(Paragraph(item['summary_document'], styles['Normal']))
        #     story.append(Spacer(1, 10))
        
        # Individual rule analysis
        individual_analysis = parse_individual_analysis(item.get('individual_rule_analysis', '[]'))
        if individual_analysis:
            story.append(Paragraph("Análise Individual das Regras", subheading_style))
            
            for rule in individual_analysis:
                rule_number = rule.get('rule_number', 'N/A')
                rule_status = 'CONFORME' if rule.get('is_compliant', False) else 'NÃO CONFORME'
                rule_color = colors.green if rule.get('is_compliant', False) else colors.red
                
                story.append(Paragraph(f"<b>Regra {rule_number}:</b> <font color='{rule_color}'>{rule_status}</font>", styles['Normal']))
                
                if rule.get('rule_text'):
                    story.append(Paragraph(f"<b>Texto da Regra:</b> {rule['rule_text']}", styles['Normal']))
                
                if rule.get('reasoning'):
                    story.append(Paragraph(f"<b>Análise:</b> {rule['reasoning']}", styles['Normal']))
                
                citations = rule.get('citations', [])
                if citations:
                    story.append(Paragraph("<b>Citações:</b>", styles['Normal']))
                    for citation in citations:
                        story.append(Paragraph(f"• {citation}", styles['Normal']))
                
                story.append(Spacer(1, 10))
        
        story.append(PageBreak())
    
    # Footer
    story.append(Paragraph(f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)))
    
    # Build PDF
    doc.build(story)
    
    # Get the PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

# Fetch data
with st.spinner("Carregando dados de conformidade..."):
    compliance_data = fetch_compliance_data()

if not compliance_data:
    st.warning("Nenhum dado de conformidade encontrado. Execute a análise de conformidade primeiro.")
    st.stop()

# Convert to DataFrame for easier manipulation
df = pd.DataFrame(compliance_data)

# Sidebar filters
st.sidebar.header("🔍 Filtros")

# Filter by compliance status
compliance_filter = st.sidebar.selectbox(
    "Status de Conformidade",
    ["Todos", "Conforme", "Não Conforme"],
    index=0
)

# Filter by article number
article_numbers = sorted(df['article_number'].unique())
selected_articles = st.sidebar.multiselect(
    "Números dos Artigos",
    article_numbers,
    default=article_numbers[:5] if len(article_numbers) > 5 else article_numbers
)

# Apply filters
filtered_df = df.copy()

if compliance_filter != "Todos":
    is_compliant = compliance_filter == "Conforme"
    filtered_df = filtered_df[filtered_df['is_compliant'] == is_compliant]

if selected_articles:
    filtered_df = filtered_df[filtered_df['article_number'].isin(selected_articles)]

# Display summary statistics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total de Análises", len(filtered_df))

with col2:
    compliant_count = len(filtered_df[filtered_df['is_compliant'] == True])
    st.metric("Artigos Conformes", compliant_count)

with col3:
    non_compliant_count = len(filtered_df[filtered_df['is_compliant'] == False])
    st.metric("Artigos Não Conformes", non_compliant_count)

with col4:
    if len(filtered_df) > 0:
        compliance_rate = (compliant_count / len(filtered_df)) * 100
        st.metric("Taxa de Conformidade", f"{compliance_rate:.1f}%")

# PDF Export Section
st.divider()
st.subheader("📄 Exportar Relatórios")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📊 Exportar Relatório Completo (PDF)", type="primary"):
        try:
            # Generate PDF with all filtered data
            pdf_data = generate_compliance_pdf(filtered_df.to_dict('records'))
            
            # Create download button
            st.download_button(
                label="⬇️ Baixar Relatório PDF",
                data=pdf_data,
                file_name=f"relatorio_conformidade_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

with col2:
    # CVM175 PDF download - try multiple possible paths
    cvm175_paths = [
        "/usr/pkg/app/documents/resol175consolid.pdf",  # AWS EC2 path
        "/Users/joaovitorresendesoares/Documents/schema_manager/src/cvm_sections/resol175consolid.pdf",  # Local path
        "./documents/resol175consolid.pdf",  # Relative path
        "resol175consolid.pdf"  # Current directory
    ]
    
    cvm175_found = False
    for cvm175_path in cvm175_paths:
        try:
            with open(cvm175_path, "rb") as pdf_file:
                pdf_data = pdf_file.read()
            
            st.download_button(
                label="📋 Baixar CVM175 Original",
                data=pdf_data,
                file_name="CVM175_Resolucao_Consolidada.pdf",
                mime="application/pdf",
                type="secondary"
            )
            st.caption("Resolução CVM 175 - Documento Original")
            cvm175_found = True
            break
        except FileNotFoundError:
            continue
        except Exception as e:
            continue
    
    if not cvm175_found:
        st.warning("⚠️ Arquivo CVM175 não encontrado")
        st.caption("Arquivo deve ser copiado para o servidor")

with col3:
    # Fund PDF download - try multiple possible paths
    fund_paths = [
        "/usr/pkg/app/documents/48964604000184-REG06022025V01-000832682.pdf",  # AWS EC2 path
        "/Users/joaovitorresendesoares/Documents/Z/RAG/legacy/extraction_pipeline/pdfs/48964604000184-REG06022025V01-000832682.pdf",  # Local path
        "./documents/48964604000184-REG06022025V01-000832682.pdf",  # Relative path
        "48964604000184-REG06022025V01-000832682.pdf"  # Current directory
    ]
    
    fund_found = False
    for fund_path in fund_paths:
        try:
            with open(fund_path, "rb") as pdf_file:
                pdf_data = pdf_file.read()
            
            st.download_button(
                label="📄 Baixar Fundo Original",
                data=pdf_data,
                file_name="Regulamento_Fundo_Original.pdf",
                mime="application/pdf",
                type="secondary"
            )
            st.caption("Regulamento do Fundo - Documento Original")
            fund_found = True
            break
        except FileNotFoundError:
            continue
        except Exception as e:
            continue
    
    if not fund_found:
        st.warning("⚠️ Arquivo do Fundo não encontrado")
        st.caption("Arquivo deve ser copiado para o servidor")

st.divider()

# Main data table
st.header("📋 Tabela de Conformidade")

# Create a more detailed table
display_df = filtered_df.copy()
display_df['status'] = display_df['is_compliant'].map({True: '✅ Conforme', False: '❌ Não Conforme'})

# Select columns to display
columns_to_show = ['article_number', 'chapter', 'section', 'status']
display_df = display_df[columns_to_show]

# Rename columns for better display
display_df.columns = ['Artigo', 'Capítulo', 'Seção', 'Status']

# Display the table
st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

st.divider()

# Detailed view for selected article
st.header("🔍 Análise Detalhada")

if len(filtered_df) > 0:
    # Article selector
    article_options = []
    for _, row in filtered_df.iterrows():
        label = f"Artigo {row['article_number']} - {row['chapter']} - {row['section']}"
        article_options.append((label, row['article_id']))
    
    selected_article_label = st.selectbox(
        "Selecione um artigo para análise detalhada:",
        [option[0] for option in article_options]
    )
    
    if selected_article_label:
        # Get the selected article data
        selected_article_id = next(option[1] for option in article_options if option[0] == selected_article_label)
        selected_article = filtered_df[filtered_df['article_id'] == selected_article_id].iloc[0]
        
        # Display article information
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📄 Informações do Artigo")
            st.write(f"**ID:** {selected_article['article_id']}")
            st.write(f"**Número:** {selected_article['article_number']}")
            st.write(f"**Capítulo:** {selected_article['chapter']}")
            st.write(f"**Seção:** {selected_article['section']}")
            st.write(f"**Status:** {'✅ Conforme' if selected_article['is_compliant'] else '❌ Não Conforme'}")
        
        with col2:
            st.subheader("📊 Resumo da Análise")
            individual_analysis = parse_individual_analysis(selected_article['individual_rule_analysis'])
            
            if individual_analysis:
                total_rules = len(individual_analysis)
                compliant_rules = sum(1 for rule in individual_analysis if rule.get('is_compliant', False))
                non_compliant_rules = total_rules - compliant_rules
                
                st.metric("Total de Regras", total_rules)
                st.metric("Regras Conformes", compliant_rules)
                st.metric("Regras Não Conformes", non_compliant_rules)
                
                if total_rules > 0:
                    compliance_rate = (compliant_rules / total_rules) * 100
                    st.metric("Taxa de Conformidade", f"{compliance_rate:.1f}%")
            else:
                st.warning("Nenhuma análise individual encontrada")
        
        # Display individual rule analysis
        st.subheader("🔍 Análise Individual das Regras")
        
        individual_analysis = parse_individual_analysis(selected_article['individual_rule_analysis'])
        
        if individual_analysis:
            for i, rule in enumerate(individual_analysis, 1):
                with st.expander(f"Regra {rule.get('rule_number', i)}: {'✅ Conforme' if rule.get('is_compliant') else '❌ Não Conforme'}"):
                    # Split layout: Left (Document) and Right (Analysis)
                    col_left, col_right = st.columns([1, 1])
                    
                    with col_left:
                        st.subheader("📄 Seção do Documento")
                        
                        # Get article information for document section display
                        try:
                            import json
                            import os
                            
                            # Get article number from the selected article
                            article_number = selected_article['article_number']
                            article_id = f"artigo{article_number}"
                            
                            # Load article metadata from S3
                            article_data = get_article_by_id(article_id)
                            
                            if article_data:
                                st.write("**Localização da Regra:**")
                                st.write(f"• Artigo: {article_data['article_id']}")
                                st.write(f"• Página: {article_data.get('page_number', 'N/A')}")
                                st.write(f"• Capítulo: {article_data['article_metadata'].get('related_chapter', 'N/A')}")
                                st.write(f"• Seção: {article_data['article_metadata'].get('related_section', 'N/A')}")
                                st.write(f"• Offset: {article_data['start_offset']} - {article_data['end_offset']}")
                                
                                # Load and show document section content from S3
                                article_content = get_article_content(article_data)
                                
                                if article_content:
                                    st.write("**Conteúdo do Artigo:**")
                                else:
                                    st.error("Erro ao carregar conteúdo do artigo do S3")
                                    article_content = ""
                                
                                # Show a preview of the article content (first 500 characters)
                                preview_length = 500
                                if len(article_content) > preview_length:
                                    preview_text = article_content[:preview_length] + "..."
                                    st.text_area(
                                        "Conteúdo do artigo (prévia)",
                                        value=preview_text,
                                        height=200,
                                        disabled=True
                                    )
                                    
                                    # Show full content in expander
                                    with st.expander("Ver conteúdo completo do artigo"):
                                        st.text_area(
                                            "Conteúdo completo",
                                            value=article_content,
                                            height=300,
                                            disabled=True
                                        )
                                else:
                                    st.text_area(
                                        "Conteúdo do artigo",
                                        value=article_content,
                                        height=200,
                                        disabled=True
                                    )
                            else:
                                st.warning("Informações do artigo não encontradas")
                                
                        except Exception as e:
                            st.error(f"Erro ao carregar informações do documento: {str(e)}")
                    
                    with col_right:
                        st.subheader("🔍 Análise da Regra")
                        
                        st.write(f"**Texto da Regra:**")
                        st.write(rule.get('rule_text', 'N/A'))
                        
                        st.write(f"**Análise:**")
                        st.write(rule.get('reasoning', 'N/A'))
                        
                        citations = rule.get('citations', [])
                        if citations:
                            st.write(f"**Citações:**")
                            for citation in citations:
                                st.write(f"• {citation}")
        else:
            st.warning("Nenhuma análise individual disponível para este artigo")
        
        # Summary document generation is disabled for now
        # st.subheader("📋 Documento de Resumo")
        # summary_doc = selected_article['summary_document']
        # if summary_doc and summary_doc != "Nenhum documento gerado":
        #     st.write(summary_doc)
        # else:
        #     st.info("Nenhum documento de resumo disponível")

else:
    st.info("Nenhum artigo encontrado com os filtros selecionados.")

# Footer
st.divider()
st.caption("💡 Dica: Use os filtros na barra lateral para refinar sua visualização dos dados de conformidade.")
