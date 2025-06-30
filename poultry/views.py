# reports/views.py
from poutryapp.models import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from datetime import datetime, timedelta
from django.db.models import Sum, Count, F, Q, Avg
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
    KeepTogether, SimpleDocTemplate
)
from django.utils import timezone
from django.db.models.functions import Trunc
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.colors import Color, HexColor
from decimal import Decimal
from datetime import datetime, time
from django.utils.timezone import make_aware

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
            filters = get_date_filter('created_at')
            data = list(EggCollection.objects.filter(filters & house_filter).select_related(
                'chicken_house', 'worker'
            ).order_by('created_at'))
            return {
                'data': data,
                'columns': ['Date', 'Chicken House', 'Worker', 'Full Trays', 'Loose Eggs', 'Rejected', 'Total Eggs'],
                'title': 'Egg Collection Report',
                'date_field': 'created_at'
            }
        
        elif report_type == 'egg_sales':
            filters = get_date_filter('created_at')
            data = list(EggSale.objects.filter(filters).select_related(
                'recorded_by'
            ).order_by('created_at'))
            return {
                'data': data,
                'columns': ['Date', 'Quantity', 'Price Per Egg', 'Total Amount', 'Buyer', 'Recorded By'],
                'title': 'Egg Sales Report',
                'date_field': 'created_at'
            }
        
        elif report_type == 'food_consumption':
            filters = get_date_filter('created_at')
            data = list(FoodDistribution.objects.filter(filters & house_filter).select_related(
                'food_type', 'chicken_house', 'distributed_by', 'received_by'
            ).order_by('created_at'))
            return {
                'data': data,
                'columns': ['Date', 'Food Type', 'Chicken House', 'Sacks Distributed', 'Distributed By', 'Received By'],
                'title': 'Food Consumption Report',
                'date_field': 'created_at'
            }
        
        elif report_type == 'medicine_usage':
            filters = get_date_filter('created_at')
            data = list(MedicineDistribution.objects.filter(filters & house_filter).select_related(
                'medicine', 'chicken_house', 'distributed_by', 'received_by'
            ).order_by('created_at'))
            return {
                'data': data,
                'columns': ['Date', 'Medicine', 'Chicken House', 'Quantity', 'Purpose', 'Distributed By', 'Received By'],
                'title': 'Medicine Usage Report',
                'date_field': 'created_at'
            }
        
        elif report_type == 'mortality':
            filters = get_date_filter('created_at')
            data = list(ChickenDeathRecord.objects.filter(filters & house_filter).select_related(
                'chicken_house', 'recorded_by', 'confirmed_by'
            ).order_by('created_at'))
            return {
                'data': data,
                'columns': ['Date', 'Chicken House', 'Number Dead', 'Possible Cause', 'Recorded By', 'Confirmed By'],
                'title': 'Chicken Mortality Report',
                'date_field': 'created_at'
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
            filters = get_date_filter('created_at')
            houses = ChickenHouse.objects.all_objects()
            productivity_data = []
            
            for house in houses:
                eggs_agg = EggCollection.objects.filter(
                    chicken_house=house,
                    **({'created_at__range': [start_date, end_date]} if start_date and end_date else {})
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


class FinancialDashboardReport(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Validate dates
        try:
            if start_date:
                start_date = make_aware(datetime.combine(datetime.strptime(start_date, '%Y-%m-%d'), time.min))
            if end_date:
                end_date = make_aware(datetime.combine(datetime.strptime(end_date, '%Y-%m-%d'), time.max))
        except (ValueError, TypeError):
            pass

        
        # Calculate date filters
        created_at_filter = Q()
        if start_date and end_date:
            created_at_filter &= Q(created_at__range=[start_date, end_date])
             
        # Financial KPIs
        total_egg_sales = EggSale.objects.filter(created_at_filter).aggregate(
            total=Sum(F('quantity') * F('price_per_egg')))
        
        total_expenses = Expense.objects.filter(created_at_filter).aggregate(
            total=Sum('total_cost'))
        
        food_purchases = FoodPurchase.objects.filter(created_at_filter).aggregate(
            total=Sum(F('sacks_purchased') * F('price_per_sack')))
        
        medicine_purchases = MedicinePurchase.objects.filter(created_at_filter).aggregate(
            total=Sum(F('quantity') * F('price_per_unit')))
        
        salary_expenses = SalaryPayment.objects.filter(created_at_filter).aggregate(
            total=Sum('amount'))
        
        # Productivity metrics
        egg_collections = EggCollection.objects.filter(created_at_filter).aggregate(
            total=Sum(F('full_trays') * 30 + F('loose_eggs')))
        
        mortality_rate = ChickenDeathRecord.objects.filter(created_at_filter).aggregate(
            total=Sum('number_dead'))
        
        # Prepare response data
        report_data = {
            'period': {
                'start': start_date.strftime('%Y-%m-%d') if start_date else 'All time',
                'end': end_date.strftime('%Y-%m-%d') if end_date else 'Present'
            },
            'financial_summary': {
                'total_revenue': float(total_egg_sales['total'] or 0),
                'total_expenses': float(total_expenses['total'] or 0),
                'gross_profit': float((total_egg_sales['total'] or 0) - (total_expenses['total'] or 0)),
                'expense_breakdown': {
                    'food': float(food_purchases['total'] or 0),
                    'medicine': float(medicine_purchases['total'] or 0),
                    'salaries': float(salary_expenses['total'] or 0),
                    'other': float((total_expenses['total'] or 0) - 
                            (food_purchases['total'] or 0) - 
                            (medicine_purchases['total'] or 0) - 
                            (salary_expenses['total'] or 0))
                }
            },
            'productivity_metrics': {
                'eggs_produced': egg_collections['total'] or 0,
                'mortality_rate': mortality_rate['total'] or 0,
                'avg_eggs_per_hen': self.calculate_avg_eggs_per_hen(start_date, end_date)
            },
            'comparative_analysis': self.get_comparative_analysis(start_date, end_date)
        }
        
        format = request.query_params.get('report_format', 'json')
        if format == 'pdf':
            return self.generate_pdf_report(report_data)
        elif format == 'csv':
            return self.generate_csv_report(report_data)
        else:
            return Response(report_data)
    
    def calculate_avg_eggs_per_hen(self, start_date, end_date):
        """Calculate average eggs produced per chicken across all houses"""
        date_filter = Q()
        if start_date and end_date:
            date_filter &= Q(created_at__range=[start_date, end_date])
        
        total_eggs = EggCollection.objects.filter(date_filter).aggregate(
            total=Sum(F('full_trays') * 30 + F('loose_eggs')))['total'] or 0
        
        avg_chickens = ChickenHouse.objects.aggregate(
            avg=Avg('current_chicken_count'))['avg'] or 0
        
        return round(total_eggs / avg_chickens, 2) if avg_chickens > 0 else 0
    
    def get_comparative_analysis(self, start_date, end_date):
        """Compare performance across chicken houses"""
        date_filter = Q()
        if start_date and end_date:
            date_filter &= Q(created_at__range=[start_date, end_date])
        
        houses = ChickenHouse.objects.all_objects()
        analysis = []
        
        for house in houses:
            # Egg production
            eggs = EggCollection.objects.filter(
                Q(chicken_house=house) & date_filter
            ).aggregate(
                total=Sum(F('full_trays') * 30 + F('loose_eggs'))
            )['total'] or 0

            # Food consumption
            food = FoodDistribution.objects.filter(
                Q(chicken_house=house) & date_filter
            ).aggregate(
                total=Sum('sacks_distributed')
            )['total'] or 0

            # Mortality
            deaths = ChickenDeathRecord.objects.filter(
                Q(chicken_house=house) & date_filter
            ).aggregate(
                total=Sum('number_dead')
            )['total'] or 0
            
            # Calculate efficiency metrics
            egg_per_sack = (eggs / food) if food and food > 0 else 0
            mortality_rate = (deaths / house.current_chicken_count) * 100 if house.current_chicken_count > 0 else 0
            
            analysis.append({
                'house': house.name,
                'eggs_produced': eggs or 0,
                'food_consumed': round(food or 0, 2),
                'deaths': deaths or 0,
                'egg_per_sack': round(egg_per_sack, 2),
                'mortality_rate': round(mortality_rate, 2),
                'current_chickens': house.current_chicken_count,
                'age_in_weeks': house.age_in_weeks,
                'avg_weight': house.average_weight
            })
        
        return analysis
    
    def generate_pdf_report(self, report_data):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontSize=18,
            textColor=colors.darkblue,
            spaceAfter=12,
            alignment=1
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=6
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph(
            f"Financial Performance Dashboard ({report_data['period']['start']} to {report_data['period']['end']})", 
            title_style))
        
        # Financial Summary
        elements.append(Paragraph("Financial Summary", subtitle_style))
        
        financial_data = [
            ["Metric", "Amount"],
            ["Total Revenue", f"KES {report_data['financial_summary']['total_revenue']:,.2f}"],
            ["Total Expenses", f"KES {report_data['financial_summary']['total_expenses']:,.2f}"],
            ["Gross Profit", f"KES {report_data['financial_summary']['gross_profit']:,.2f}"]
        ]
        
        financial_table = Table(financial_data)
        financial_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ]))
        
        elements.append(financial_table)
        elements.append(Spacer(1, 12))
        
        # Expense Breakdown Pie Chart
        expense_data = [
            ["Food", report_data['financial_summary']['expense_breakdown']['food']],
            ["Medicine", report_data['financial_summary']['expense_breakdown']['medicine']],
            ["Salaries", report_data['financial_summary']['expense_breakdown']['salaries']],
            ["Other", report_data['financial_summary']['expense_breakdown']['other']]
        ]
        
        # Create a drawing object
        drawing = Drawing(400, 200)

        # Create pie chart
        pie = Pie()
        pie.x = 150
        pie.y = 50
        pie.width = 300
        pie.height = 200
        pie.data = [item[1] for item in expense_data]
        pie.labels = [item[0] for item in expense_data]
        pie.slices.strokeWidth = 0.5

        # Customize slice colors if desired
        pie.slices[0].fillColor = HexColor('#4e79a7')
        pie.slices[1].fillColor = HexColor('#f28e2b')
        pie.slices[2].fillColor = HexColor('#e15759')
        pie.slices[3].fillColor = HexColor('#76b7b2')

        # Add chart to drawing
        drawing.add(pie)
        elements.append(Paragraph("Expense Breakdown", subtitle_style))
        elements.append(drawing)
        elements.append(Spacer(1, 12))
        
        # Productivity Metrics
        elements.append(Paragraph("Productivity Metrics", subtitle_style))
        
        prod_data = [
            ["Metric", "Value"],
            ["Total Eggs Produced", report_data['productivity_metrics']['eggs_produced']],
            ["Mortality Count", report_data['productivity_metrics']['mortality_rate']],
            ["Avg Eggs per Hen", report_data['productivity_metrics']['avg_eggs_per_hen']]
        ]
        
        prod_table = Table(prod_data)
        prod_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ]))
        
        elements.append(prod_table)
        elements.append(Spacer(1, 12))
        
        # Comparative Analysis
        elements.append(Paragraph("House Performance Comparison", subtitle_style))
        
        comp_headers = ["House", "Eggs", "Food (sacks)", "Deaths", "Eggs/Sack", "Mortality %", "Chickens", "Age (weeks)", "Avg Weight"]
        comp_data = [comp_headers]
        
        for house in report_data['comparative_analysis']:
            comp_data.append([
                house['house'],
                house['eggs_produced'],
                house['food_consumed'],
                house['deaths'],
                house['egg_per_sack'],
                f"{house['mortality_rate']}%",
                house['current_chickens'],
                house['age_in_weeks'],
                f"{house['avg_weight']}kg"
            ])
        
        comp_table = Table(comp_data)
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ]))
        
        elements.append(comp_table)
        
        doc.build(elements)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="financial_dashboard.pdf"'
        return response


class CostOfProductionReport(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all expenses
        expenses = Expense.objects.filter(
            date__range=[start_date, end_date] if start_date and end_date else Q()
        ).values('category__name').annotate(
            total_cost=Sum('total_cost')
        ).order_by('-total_cost')
        
        # Get all egg production
        egg_production = EggCollection.objects.filter(
            created_at__range=[start_date, end_date] if start_date and end_date else Q()
        ).aggregate(
            total_eggs=Sum(F('full_trays') * 30 + F('loose_eggs'))
        )['total_eggs'] or 0
        
        # Calculate cost per egg
        total_expenses = sum([e['total_cost'] for e in expenses])
        cost_per_egg = total_expenses / egg_production if egg_production > 0 else 0
        
        # Get average chicken count
        avg_chickens = ChickenHouse.objects.aggregate(
            avg=Avg('current_chicken_count')
        )['avg'] or 0
        
        cost_per_chicken = total_expenses / Decimal(avg_chickens) if avg_chickens > 0 else Decimal('0.00')

        # cost_per_chicken = total_expenses / avg_chickens if avg_chickens > 0 else 0
        
        # Prepare response
        report_data = {
            'period': {
                'start': start_date.strftime('%Y-%m-%d') if start_date else 'All time',
                'end': end_date.strftime('%Y-%m-%d') if end_date else 'Present'
            },
            'total_eggs_produced': egg_production,
            'total_expenses': total_expenses,
            'cost_per_egg': round(cost_per_egg, 2),
            'cost_per_chicken': round(cost_per_chicken, 2),
            'expense_breakdown': list(expenses),
            'house_comparison': self.compare_house_costs(start_date, end_date)
        }
        
        format = request.query_params.get('report_format', 'json')
        if format == 'pdf':
            return self.generate_pdf_report(report_data)
        elif format == 'csv':
            return self.generate_csv_report(report_data)
        else:
            return Response(report_data)
    
    def compare_house_costs(self, start_date, end_date):
        """Compare costs and production across houses"""
        date_filter = Q()
        if start_date and end_date:
            date_filter &= Q(date__range=[start_date, end_date])
        
        houses = ChickenHouse.objects.all_objects()
        comparison = []
        
        for house in houses:
            # Get expenses for this house (food, medicine distributed to this house)
            food_cost = FoodDistribution.objects.filter(
                Q(chicken_house=house) & date_filter
            ).annotate(
                cost=F('sacks_distributed') * F('food_type__foodpurchase__price_per_sack')
            ).aggregate(
                total=Sum('cost')
            )['total'] or 0

            medicine_cost = MedicineDistribution.objects.filter(
                Q(chicken_house=house) & date_filter
            ).annotate(
                cost=F('quantity') * F('medicine__medicinepurchase__price_per_unit')
            ).aggregate(
                total=Sum('cost')
            )['total'] or 0

            # Get egg production
            eggs = EggCollection.objects.filter(
                Q(chicken_house=house) & date_filter
            ).aggregate(
                total=Sum(F('full_trays') * 30 + F('loose_eggs'))
            )['total'] or 0
            # Calculate metrics
            total_cost = food_cost + medicine_cost
            cost_per_egg = Decimal(total_cost) / Decimal(eggs) if eggs > 0 else Decimal('0.00')            
            cost_per_chicken = total_cost / house.current_chicken_count if house.current_chicken_count > 0 else 0
            
            comparison.append({
                'house': house.name,
                'total_cost': round(total_cost, 2),
                'food_cost': round(food_cost, 2),
                'medicine_cost': round(medicine_cost, 2),
                'eggs_produced': eggs or 0,
                'cost_per_egg': round(cost_per_egg, 2),
                'cost_per_chicken': round(cost_per_chicken, 2),
                'chicken_count': house.current_chicken_count
            })
        
        return comparison
    
    def generate_pdf_report(self, report_data):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.darkblue,
            spaceAfter=12,
            alignment=1
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.darkblue,
            spaceAfter=6
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph(
            f"Cost of Production Analysis ({report_data['period']['start']} to {report_data['period']['end']})", 
            title_style))
        
        # Summary
        elements.append(Paragraph("Key Metrics", subtitle_style))
        
        summary_data = [
            ["Metric", "Value"],
            ["Total Eggs Produced", report_data['total_eggs_produced']],
            ["Total Expenses", f"KES {report_data['total_expenses']:,.2f}"],
            ["Cost per Egg", f"KES {report_data['cost_per_egg']:,.4f}"],
            ["Cost per Chicken", f"KES {report_data['cost_per_chicken']:,.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 12))
        
        # Expense Breakdown
        elements.append(Paragraph("Expense Breakdown by Category", subtitle_style))
        
        expense_data = [["Category", "Amount (KES)"]] + [
            [e['category__name'], f"{e['total_cost']:,.2f}"] 
            for e in report_data['expense_breakdown']
        ]
        
        expense_table = Table(expense_data, colWidths=[200, 100])
        expense_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ]))
        
        elements.append(expense_table)
        elements.append(Spacer(1, 12))
        
        # House Comparison
        elements.append(Paragraph("House Comparison", subtitle_style))
        
        house_data = [
            ["House", "Total Cost", "Food Cost", "Medicine Cost", "Eggs", "Cost/Egg", "Cost/Chicken"]
        ]
        
        for house in report_data['house_comparison']:
            house_data.append([
                house['house'],
                f"{house['total_cost']:,.2f}",
                f"{house['food_cost']:,.2f}",
                f"{house['medicine_cost']:,.2f}",
                house['eggs_produced'],
                f"{house['cost_per_egg']:,.4f}",
                f"{house['cost_per_chicken']:,.2f}"
            ])
        
        house_table = Table(house_data, colWidths=[80, 70, 70, 70, 50, 70, 80])
        house_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ]))
        
        elements.append(house_table)
        
        doc.build(elements)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="cost_of_production.pdf"'
        return response

class ProfitabilityTrendReport(APIView):
    def get(self, request):
        period = request.query_params.get('period', 'monthly')  # monthly, quarterly, yearly
        num_periods = int(request.query_params.get('num_periods', 12))
        
        end_date = timezone.now().date()
        
        if period == 'monthly':
            start_date = end_date - timedelta(days=30*num_periods)
            group_by = 'month'
        elif period == 'quarterly':
            start_date = end_date - timedelta(days=90*num_periods)
            group_by = 'quarter'
        else:  # yearly
            start_date = end_date - timedelta(days=365*num_periods)
            group_by = 'year'
        
        # Get sales data grouped by period
        sales_by_period = self.get_sales_by_period(start_date, end_date, group_by)
        
        # Get expenses data grouped by period
        expenses_by_period = self.get_expenses_by_period(start_date, end_date, group_by)
        
        # Combine data
        periods = sorted(set(sales_by_period.keys()).union(set(expenses_by_period.keys())))
        
        trend_data = []
        for p in periods:
            sales = sales_by_period.get(p, 0)
            expenses = expenses_by_period.get(p, 0)
            profit = sales - expenses
            margin = (profit / sales) * 100 if sales > 0 else 0
            
            trend_data.append({
                'period': p,
                'sales': sales,
                'expenses': expenses,
                'profit': profit,
                'margin': round(margin, 1)
            })
        
        # Calculate averages
        avg_sales = sum([d['sales'] for d in trend_data]) / len(trend_data) if trend_data else 0
        avg_expenses = sum([d['expenses'] for d in trend_data]) / len(trend_data) if trend_data else 0
        avg_profit = sum([d['profit'] for d in trend_data]) / len(trend_data) if trend_data else 0
        avg_margin = sum([d['margin'] for d in trend_data]) / len(trend_data) if trend_data else 0
        
        report_data = {
            'period_type': period,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'trend_data': trend_data,
            'averages': {
                'sales': round(avg_sales, 2),
                'expenses': round(avg_expenses, 2),
                'profit': round(avg_profit, 2),
                'margin': round(avg_margin, 1)
            },
            'best_period': max(trend_data, key=lambda x: x['profit']) if trend_data else None,
            'worst_period': min(trend_data, key=lambda x: x['profit']) if trend_data else None
        }
        
        format = request.query_params.get('report_format', 'json')
        if format == 'pdf':
            return self.generate_pdf_report(report_data)
        elif format == 'csv':
            return self.generate_csv_report(report_data)
        else:
            return Response(report_data)
    
    def get_sales_by_period(self, start_date, end_date, group_by):
        """Get sales aggregated by time period"""
        sales = EggSale.objects.filter(
            created_at__range=[start_date, end_date]
        ).annotate(
            period=Trunc('created_at', group_by)
        ).values('period').annotate(
            total_sales=Sum(F('quantity') * F('price_per_egg'))
        ).order_by('period')
        
        return {s['period'].strftime('%Y-%m'): float(s['total_sales']) for s in sales}
    
    def get_expenses_by_period(self, start_date, end_date, group_by):
        """Get expenses aggregated by time period"""
        expenses = Expense.objects.filter(
            date__range=[start_date, end_date]
        ).annotate(
            period=Trunc('date', group_by)
        ).values('period').annotate(
            total_expenses=Sum('total_cost')).order_by('period')
        
        return {e['period'].strftime('%Y-%m'): float(e['total_expenses']) for e in expenses}
    
    def generate_pdf_report(self, report_data):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.darkblue,
            spaceAfter=12,
            alignment=1
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.darkblue,
            spaceAfter=6
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph(
            f"Profitability Trend Analysis ({report_data['start_date']} to {report_data['end_date']})", 
            title_style))
        
        # Summary
        elements.append(Paragraph("Performance Summary", subtitle_style))
        
        summary_data = [
            ["Metric", "Average", "Best Period", "Worst Period"],
            ["Sales (KES)", 
             f"{report_data['averages']['sales']:,.2f}", 
             f"{report_data['best_period']['sales']:,.2f} ({report_data['best_period']['period']})" if report_data['best_period'] else 'N/A',
             f"{report_data['worst_period']['sales']:,.2f} ({report_data['worst_period']['period']})" if report_data['worst_period'] else 'N/A'],
            ["Expenses (KES)", 
             f"{report_data['averages']['expenses']:,.2f}", 
             f"{report_data['best_period']['expenses']:,.2f} ({report_data['best_period']['period']})" if report_data['best_period'] else 'N/A',
             f"{report_data['worst_period']['expenses']:,.2f} ({report_data['worst_period']['period']})" if report_data['worst_period'] else 'N/A'],
            ["Profit (KES)", 
             f"{report_data['averages']['profit']:,.2f}", 
             f"{report_data['best_period']['profit']:,.2f} ({report_data['best_period']['period']})" if report_data['best_period'] else 'N/A',
             f"{report_data['worst_period']['profit']:,.2f} ({report_data['worst_period']['period']})" if report_data['worst_period'] else 'N/A'],
            ["Margin (%)", 
             f"{report_data['averages']['margin']}%", 
             f"{report_data['best_period']['margin']}% ({report_data['best_period']['period']})" if report_data['best_period'] else 'N/A',
             f"{report_data['worst_period']['margin']}% ({report_data['worst_period']['period']})" if report_data['worst_period'] else 'N/A']
        ]
        
        summary_table = Table(summary_data, colWidths=[120, 100, 150, 150])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 12))
        
        # Trend Data
        elements.append(Paragraph("Detailed Trend Data", subtitle_style))
        
        trend_headers = ["Period", "Sales (KES)", "Expenses (KES)", "Profit (KES)", "Margin (%)"]
        trend_data = [trend_headers]
        
        for period in report_data['trend_data']:
            trend_data.append([
                period['period'],
                f"{period['sales']:,.2f}",
                f"{period['expenses']:,.2f}",
                f"{period['profit']:,.2f}",
                f"{period['margin']}%"
            ])
        
        trend_table = Table(trend_data, colWidths=[80, 100, 100, 100, 80])
        trend_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ]))
        
        elements.append(trend_table)
        elements.append(Spacer(1, 12))
        
        # Trend Chart
        elements.append(Paragraph("Profitability Trend", subtitle_style))
        
        drawing = Drawing(600, 300)
        
        # Prepare data for chart
        periods = [d['period'] for d in report_data['trend_data']]
        sales = [d['sales'] for d in report_data['trend_data']]
        expenses = [d['expenses'] for d in report_data['trend_data']]
        profits = [d['profit'] for d in report_data['trend_data']]
        
        # Create line chart
        # Create line chart
        lc = HorizontalLineChart()
        lc.x = 50
        lc.y = 50
        lc.height = 250
        lc.width = 550
        lc.data = [sales, expenses, profits]
        lc.strokeColor = colors.black
        lc.valueAxis.valueMin = min(0, min(profits)) - 1000
        lc.valueAxis.valueMax = max(sales) + 1000
        lc.categoryAxis.categoryNames = periods

        # Customize line colors
        lc.lines[0].strokeColor = colors.green
        lc.lines[1].strokeColor = colors.red
        lc.lines[2].strokeColor = colors.blue
        lc.lines[0].name = 'Sales'
        lc.lines[1].name = 'Expenses'
        lc.lines[2].name = 'Profit'

        # Add value labels
        lc.lineLabelArray = [[f"{v:,.0f}" for v in series] for series in lc.data]

        # Add chart to drawing
        drawing.add(lc)
        elements.append(drawing)
        
        doc.build(elements)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="profitability_trend.pdf"'
        return response