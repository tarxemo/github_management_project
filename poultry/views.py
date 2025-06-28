# reports/views.py
from poutryapp.models import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from datetime import datetime
from django.db.models import Sum, Count, F, Q
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import csv
from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, 
    Paragraph, Table, TableStyle, Spacer,
    KeepTogether
)


class ReportAPIView(APIView):
    def get(self, request):
        report_type = request.query_params.get('type')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        house_id = request.query_params.get('house_id')
        format = request.query_params.get('report_format', 'pdf_format')

        # Validate dates
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get report data based on type
        report_data = self.get_report_data(report_type, start_date, end_date, house_id)
        
        if not report_data:
            return Response(
                {"error": "Invalid report type or no data available"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate report in requested format
        if format == 'csv_format':
            return self.generate_csv(report_type, report_data)
        else:  # default to PDF
            return self.generate_pdf(report_type, report_data)

    def get_report_data(self, report_type, start_date, end_date, house_id):
        """Retrieve data based on report type and filters"""
        def get_date_filter(model_field):
            filters = Q()
            if start_date and end_date:
                filters &= Q(**{f"{model_field}__range": [start_date, end_date]})
            elif start_date:
                filters &= Q(**{f"{model_field}__gte": start_date})
            elif end_date:
                filters &= Q(**{f"{model_field}__lte": end_date})
            return filters

        house_filter = Q()
        if house_id:
            house_filter &= Q(chicken_house_id=house_id)

        if report_type == 'egg_collection':
            filters = get_date_filter('date_collected')
            data = list(EggCollection.objects.filter(filters & house_filter).select_related(
                'chicken_house', 'worker'
            ).order_by('date_collected'))
            return {
                'data': data,
                'columns': ['Date', 'Chicken House', 'Worker', 'Full Trays', 'Loose Eggs', 'Rejected', 'Total Eggs'],
                'title': 'Egg Collection Report',
                'date_field': 'date_collected'
            }
        
        elif report_type == 'egg_sales':
            filters = get_date_filter('date_sold')
            data = list(EggSale.objects.filter(filters).select_related(
                'recorded_by'
            ).order_by('date_sold'))
            return {
                'data': data,
                'columns': ['Date', 'Quantity', 'Price Per Egg', 'Total Amount', 'Buyer', 'Recorded By'],
                'title': 'Egg Sales Report',
                'date_field': 'date_sold'
            }
        
        elif report_type == 'food_consumption':
            filters = get_date_filter('date_distributed')
            data = list(FoodDistribution.objects.filter(filters & house_filter).select_related(
                'food_type', 'chicken_house', 'distributed_by', 'received_by'
            ).order_by('date_distributed'))
            return {
                'data': data,
                'columns': ['Date', 'Food Type', 'Chicken House', 'Sacks Distributed', 'Distributed By', 'Received By'],
                'title': 'Food Consumption Report',
                'date_field': 'date_distributed'
            }
        
        elif report_type == 'medicine_usage':
            filters = get_date_filter('date_distributed')
            data = list(MedicineDistribution.objects.filter(filters & house_filter).select_related(
                'medicine', 'chicken_house', 'distributed_by', 'received_by'
            ).order_by('date_distributed'))
            return {
                'data': data,
                'columns': ['Date', 'Medicine', 'Chicken House', 'Quantity', 'Purpose', 'Distributed By', 'Received By'],
                'title': 'Medicine Usage Report',
                'date_field': 'date_distributed'
            }
        
        elif report_type == 'mortality':
            filters = get_date_filter('date_recorded')
            data = list(ChickenDeathRecord.objects.filter(filters & house_filter).select_related(
                'chicken_house', 'recorded_by', 'confirmed_by'
            ).order_by('date_recorded'))
            return {
                'data': data,
                'columns': ['Date', 'Chicken House', 'Number Dead', 'Possible Cause', 'Recorded By', 'Confirmed By'],
                'title': 'Chicken Mortality Report',
                'date_field': 'date_recorded'
            }
        
        elif report_type == 'expenses':
            filters = get_date_filter('date')
            data = list(Expense.objects.filter(filters).select_related(
                'category', 'recorded_by'
            ).order_by('date'))
            return {
                'data': data,
                'columns': ['Date', 'Category', 'Description', 'Payment Method', 'Quantity', 'Unit Cost', 'Total Cost', 'Recorded By'],
                'title': 'Expenses Report',
                'date_field': 'date'
            }
        
        elif report_type == 'productivity':
            filters = get_date_filter('date_collected')
            houses = ChickenHouse.objects.all()
            productivity_data = []
            
            for house in houses:
                eggs_agg = EggCollection.objects.filter(
                    chicken_house=house,
                    **({'date_collected__range': [start_date, end_date]} if start_date and end_date else {})
                ).aggregate(total_eggs=Sum(F('full_trays') * 30 + F('loose_eggs')))
                
                eggs = eggs_agg['total_eggs'] or 0
                avg_chickens = house.current_chicken_count
                productivity = (eggs / avg_chickens) if avg_chickens > 0 else 0
                
                productivity_data.append({
                    'house': house.name,
                    'total_eggs': eggs,
                    'avg_chickens': avg_chickens,
                    'productivity': round(productivity, 2)
                })
            
            return {
                'data': productivity_data,
                'columns': ['Chicken House', 'Total Eggs', 'Average Chickens', 'Eggs per Chicken'],
                'title': 'Productivity Report',
                'date_field': None
            }

        return None


    def generate_pdf(self, report_type, report_data):
        buffer = BytesIO()
        
        # Import page sizes at the top of your file
        from reportlab.lib.pagesizes import A4
        
        # Use A4 size in portrait mode
        doc = BaseDocTemplate(
            buffer, 
            pagesize=A4,
            leftMargin=50,
            rightMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        width, height = A4  # Standard A4 dimensions (595.27 x 841.89 points)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.HexColor("#1F1E24"),
            spaceAfter=12,
            alignment=1  # Center aligned
        )
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.white,
            alignment=1,
            leading=12
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            leading=10
        )
        
        # Title
        title = Paragraph(report_data['title'], title_style)
        
        # Date range if applicable
        date_text = ""
        if report_type == 'productivity' and report_data.get('date_field') and report_data['data']:
            date_text = f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        
        # Prepare table data
        table_data = []
        table_data.append([Paragraph(col, header_style) for col in report_data['columns']])
        
        # Add data rows
        for item in report_data['data']:
            row = []
            for col in report_data['columns']:
                col_key = col.lower().replace(' ', '_')
                if isinstance(item, dict):
                    value = str(item.get(col_key, ''))
                else:
                    value = str(getattr(item, col_key, ''))
                row.append(Paragraph(value, body_style))
            table_data.append(row)
        
        # Calculate column widths
        available_width = width - doc.leftMargin - doc.rightMargin
        num_cols = len(report_data['columns'])
        col_widths = [available_width / num_cols for _ in report_data['columns']]
        
        # Create table with automatic row splitting
        table = Table(
            table_data,
            colWidths=col_widths,
            repeatRows=1,  # Repeat headers on each page
            hAlign='LEFT'
        )
        
        # Table style
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEADING', (0, 0), (-1, -1), 11),
        ]))
        
        # Create a template for each page
        def on_first_page(canvas, doc):
            canvas.saveState()
            # Draw header
            title.wrap(available_width, 30)
            title.drawOn(canvas, doc.leftMargin, height - doc.topMargin - 30)
            
            if date_text:
                canvas.setFont("Helvetica", 10)
                canvas.drawString(doc.leftMargin, height - doc.topMargin - 50, date_text)
            
            # Draw footer
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.grey)
            canvas.drawRightString(width - doc.rightMargin, doc.bottomMargin/2, 
                                 f"Page 1 - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            canvas.restoreState()
        
        def on_later_pages(canvas, doc):
            canvas.saveState()
            # Draw footer with page number
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.grey)
            canvas.drawRightString(width - doc.rightMargin, doc.bottomMargin/2, 
                                 f"Page {doc.page} - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            canvas.restoreState()
        
        # Create frame for content
        frame = Frame(
            doc.leftMargin, 
            doc.bottomMargin, 
            available_width, 
            height - doc.topMargin - doc.bottomMargin - 60,  # Leave space for header/footer
            leftPadding=0,
            bottomPadding=0,
            rightPadding=0,
            topPadding=0,
            showBoundary=0
        )
        
        # Create page template
        doc_template = PageTemplate(
            id='AllPages',
            frames=[frame],
            onPage=on_first_page,
            onPageEnd=on_later_pages
        )
        
        doc.addPageTemplates([doc_template])
        
        # Build the document
        story = [table]
        doc.build(story)
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
        return response
    
    def generate_csv(self, report_type, report_data):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(report_data['columns'])
        
        for item in report_data['data']:
            row = []
            for col in report_data['columns']:
                col_key = col.lower().replace(' ', '_')
                if isinstance(item, dict):
                    value = item.get(col_key, '')
                else:
                    value = getattr(item, col_key, '')
                row.append(str(value))
            writer.writerow(row)
        
        return response