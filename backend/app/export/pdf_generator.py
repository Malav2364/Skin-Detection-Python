"""
PDF Report Generator for body measurements and skin tone analysis
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics import renderPDF
import qrcode
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generate professional PDF reports for body measurements"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.page_width, self.page_height = A4
        
        # Custom styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2C3E50')
        )
    
    def generate_report(self, capture_data: Dict[str, Any]) -> bytes:
        """
        Generate complete PDF report
        
        Args:
            capture_data: Dictionary containing capture results
        
        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build content
        story = []
        
        # Title
        story.append(Paragraph("Body Measurement Report", self.title_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Metadata
        capture_id = capture_data.get('capture_id', 'N/A')
        timestamp = capture_data.get('timestamp', datetime.now().isoformat())
        
        metadata_text = f"<b>Report ID:</b> {capture_id}<br/><b>Generated:</b> {timestamp}"
        story.append(Paragraph(metadata_text, self.body_style))
        story.append(Spacer(1, 0.3 * inch))
        
        # Body Measurements Section
        story.append(Paragraph("Body Measurements", self.heading_style))
        measurements_table = self._create_measurements_table(capture_data.get('metrics', {}))
        story.append(measurements_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Skin Tone Analysis Section
        if capture_data.get('skin'):
            story.append(Paragraph("Skin Tone Analysis", self.heading_style))
            skin_content = self._create_skin_analysis(capture_data['skin'])
            story.extend(skin_content)
            story.append(Spacer(1, 0.3 * inch))
        
        # Color Palette Section
        if capture_data.get('skin', {}).get('palette'):
            story.append(Paragraph("Recommended Color Palette", self.heading_style))
            palette_content = self._create_color_palette(capture_data['skin']['palette'])
            story.extend(palette_content)
            story.append(Spacer(1, 0.3 * inch))
        
        # Quality Metrics
        if capture_data.get('quality'):
            story.append(Paragraph("Quality Metrics", self.heading_style))
            quality_table = self._create_quality_table(capture_data['quality'])
            story.append(quality_table)
            story.append(Spacer(1, 0.3 * inch))
        
        # QR Code for sharing
        story.append(Paragraph("Share This Report", self.heading_style))
        qr_image = self._create_qr_code(capture_id)
        story.append(qr_image)
        story.append(Paragraph(
            f"Scan to view online: {capture_id}",
            self.body_style
        ))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated PDF report for capture {capture_id}")
        
        return pdf_bytes
    
    def _create_measurements_table(self, metrics: Dict[str, float]) -> Table:
        """Create formatted measurements table"""
        data = [
            ['Measurement', 'Value'],
            ['Height', f"{metrics.get('height_cm', 0):.1f} cm"],
            ['Shoulder Width', f"{metrics.get('shoulder_width_cm', 0):.1f} cm"],
            ['Chest Circumference', f"{metrics.get('chest_circumference_cm', 0):.1f} cm"],
            ['Waist Circumference', f"{metrics.get('waist_circumference_cm', 0):.1f} cm"],
            ['Hip Circumference', f"{metrics.get('hip_circumference_cm', 0):.1f} cm"],
            ['Inseam', f"{metrics.get('inseam_cm', 0):.1f} cm"],
            ['Torso Length', f"{metrics.get('torso_length_cm', 0):.1f} cm"],
            ['Neck Circumference', f"{metrics.get('neck_circumference_cm', 0):.1f} cm"],
        ]
        
        table = Table(data, colWidths=[3 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        return table
    
    def _create_skin_analysis(self, skin_data: Dict[str, Any]) -> list:
        """Create skin tone analysis content"""
        content = []
        
        # Skin tone metrics
        ita = skin_data.get('ita', 0)
        monk = skin_data.get('monk_bucket', 0)
        undertone = skin_data.get('undertone', 'unknown')
        
        data = [
            ['Metric', 'Value'],
            ['ITA Value', f"{ita:.2f}"],
            ['Monk Scale', f"{monk}/10"],
            ['Undertone', undertone.capitalize()],
        ]
        
        if skin_data.get('lab'):
            lab = skin_data['lab']
            data.append(['LAB L*', f"{lab.get('L', 0):.2f}"])
            data.append(['LAB a*', f"{lab.get('a', 0):.2f}"])
            data.append(['LAB b*', f"{lab.get('b', 0):.2f}"])
        
        table = Table(data, colWidths=[2.5 * inch, 2.5 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        content.append(table)
        
        return content
    
    def _create_color_palette(self, palette: list) -> list:
        """Create color palette swatches"""
        content = []
        
        # Create color swatches
        data = [['Color', 'Hex', 'Recommendation']]
        
        for color in palette:
            # Create color swatch
            drawing = Drawing(30, 20)
            rect = Rect(0, 0, 30, 20, fillColor=colors.HexColor(color['hex']))
            drawing.add(rect)
            
            data.append([
                drawing,
                color['hex'],
                color.get('reason', color.get('name', ''))
            ])
        
        table = Table(data, colWidths=[0.8 * inch, 1.2 * inch, 3 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9B59B6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        content.append(table)
        
        return content
    
    def _create_quality_table(self, quality: Dict[str, Any]) -> Table:
        """Create quality metrics table"""
        data = [
            ['Quality Check', 'Status'],
            ['Lighting Quality', '✓' if quality.get('lighting_ok') else '✗'],
            ['Reference Card Detected', '✓' if quality.get('card_detected') else '✗'],
            ['Overall Confidence', f"{quality.get('overall_confidence', 0):.1%}"],
        ]
        
        table = Table(data, colWidths=[3 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        return table
    
    def _create_qr_code(self, capture_id: str) -> Image:
        """Create QR code for sharing"""
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # URL to share (update with your actual domain)
        share_url = f"https://your-app.com/capture/{capture_id}"
        qr.add_data(share_url)
        qr.make(fit=True)
        
        # Create image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to BytesIO
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Create ReportLab Image
        img = Image(buffer, width=1.5 * inch, height=1.5 * inch)
        
        return img
