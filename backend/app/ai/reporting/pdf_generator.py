from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.app.ai.contracts import DecisionResult, EvidenceObject


class VeriSurePDFGenerator:
    """
    Generates professional, publication-quality PDF risk assessment reports using ReportLab.
    """
    @staticmethod
    def generate_report(
        output_pdf_path: str,
        scan_id: str,
        product_metadata: dict[str, Any],
        decision: DecisionResult,
        evidences: list[EvidenceObject],
        quality_details: dict[str, Any] | None = None
    ) -> str:
        doc = SimpleDocTemplate(
            output_pdf_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1e3a8a"),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=12
        )
        h2_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1e3a8a"),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "BodyTextCustom",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1f2937")
        )
        disclaimer_style = ParagraphStyle(
            "DisclaimerText",
            parent=styles["Italic"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#6b7280")
        )

        story = []

        # 1. Header & Title
        story.append(Paragraph("VeriSure AI", title_style))
        story.append(Paragraph("Product Authenticity Risk Assessment & Brand Protection Platform", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=12))

        # 2. Metadata Overview Table
        brand_name = product_metadata.get("brand", "AMUL")
        product_name = product_metadata.get("product", "Amul Dairy Product")
        variant_name = product_metadata.get("variant", "Standard")
        pack_size = product_metadata.get("pack_size", "1L")
        version_code = product_metadata.get("packaging_version", "V1")

        meta_data = [
            [
                Paragraph("<b>Scan ID:</b>", body_style), Paragraph(scan_id, body_style),
                Paragraph("<b>Date & Time:</b>", body_style), Paragraph(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), body_style)
            ],
            [
                Paragraph("<b>Brand:</b>", body_style), Paragraph(brand_name, body_style),
                Paragraph("<b>Product:</b>", body_style), Paragraph(product_name, body_style)
            ],
            [
                Paragraph("<b>Variant:</b>", body_style), Paragraph(variant_name, body_style),
                Paragraph("<b>Pack Size / Ver:</b>", body_style), Paragraph(f"{pack_size} ({version_code})", body_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[90, 180, 90, 180])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 12))

        # 3. Decision & Risk Gauge Block
        state_color = "#16a34a" if decision.risk_score < 25 else ("#eab308" if decision.risk_score < 50 else "#dc2626")
        risk_text = (
            f"<font color='{state_color}'><b>{decision.state.value}</b></font> "
            f"(Risk Score: <b>{decision.risk_score}/100</b> | Confidence: <b>{round(decision.confidence * 100, 1)}%</b> | Coverage: <b>{round(decision.evidence_coverage * 100, 1)}%</b>)"
        )
        story.append(Paragraph("Executive Assessment Verdict", h2_style))
        story.append(Paragraph(risk_text, body_style))
        story.append(Spacer(1, 6))

        # 4. Human-Readable Explanation & Recommendation
        story.append(Paragraph("Synthesized Evidence Explanation", h2_style))
        story.append(Paragraph(decision.explanation_summary, body_style))
        story.append(Spacer(1, 6))

        story.append(Paragraph("Actionable Recommendation", h2_style))
        rec_box = Table(
            [[Paragraph(f"<b>Advisory:</b> {decision.recommendation}", body_style)]],
            colWidths=[540]
        )
        rec_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4") if decision.risk_score < 30 else colors.HexColor("#fef2f2")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#86efac") if decision.risk_score < 30 else colors.HexColor("#fca5a5")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(rec_box)
        story.append(Spacer(1, 12))

        # 5. Evidence Breakdown Table
        story.append(Paragraph("Multi-Modal Evidence Breakdown", h2_style))
        ev_rows = [["Evidence Type", "Conformity", "Certainty", "Source Engine", "Findings / Status"]]
        for ev in evidences:
            score_str = f"{round(ev.score * 100, 1)}%" if ev.availability and ev.score is not None else "N/A"
            conf_str = f"{round(ev.confidence * 100, 1)}%" if ev.availability else "N/A"
            ev_rows.append([
                ev.type.value.capitalize(),
                score_str,
                conf_str,
                ev.source,
                Paragraph(ev.explanation[:120] + ("..." if len(ev.explanation) > 120 else ""), body_style)
            ])

        ev_table = Table(ev_rows, colWidths=[80, 65, 65, 110, 220])
        ev_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(ev_table)
        story.append(Spacer(1, 16))

        # 6. Academic & Legal Disclaimer
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9ca3af"), spaceAfter=8))
        disclaimer_text = (
            "<b>IMPORTANT NOTICE & LIMITATIONS:</b> VeriSure AI is an AI-assisted authenticity risk assessment "
            "and brand protection platform. A photograph cannot verify or certify the biological, nutritional, "
            "or chemical purity of liquid contents inside a sealed container. This report reflects visual, "
            "textual, and machine-readable packaging conformity against authorized factory reference standards. "
            "This assessment does not constitute a legal certification of product origin."
        )
        story.append(Paragraph(disclaimer_text, disclaimer_style))

        # Build PDF
        doc.build(story)
        return output_pdf_path
