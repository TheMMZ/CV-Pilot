from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether

def resume_pdf(draft):
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=32, bottomMargin=32,
                                 title=draft['profile']['name'] + ' - ' + draft['job']['title'], author=draft['profile']['name'])
    body = ParagraphStyle('Body', fontName='Helvetica', fontSize=9, leading=12.5, textColor=colors.HexColor('#182a42'))
    heading = ParagraphStyle('Section', parent=body, fontName='Helvetica-Bold', fontSize=10, spaceBefore=13, spaceAfter=6)
    title = ParagraphStyle('Title', parent=body, fontName='Helvetica-Bold', fontSize=21, leading=25, spaceAfter=6)
    small = ParagraphStyle('Small', parent=body, fontSize=8, leading=11, textColor=colors.HexColor('#65758b'))
    story = []
    def text(value, style=body):
        return Paragraph(escape(str(value)).replace('\n', '<br/>'), style)
    def section(label):
        story.append(text(label.upper(), heading))
    p = draft['profile']
    story.extend([text(p['name'], title), text(p['headline']), text(' | '.join(v for v in [p['email'], p.get('phone'), 'github.com/' + p['github'] if p.get('github') else None] if v), small)])
    section('Profile'); story.append(text(p['summary']))
    section('Skills'); story.append(text(' | '.join(p['skills'])))
    section('Experience')
    for exp in p['experience']:
        rows = [Paragraph('<b>' + escape(exp['title']) + '</b>', body), text(exp['organization'] + ' | ' + exp['dates'], small)]
        rows.extend(Paragraph('&#8226; ' + escape(b), body) for b in exp.get('bullets', []))
        rows.append(Spacer(1, 7))
        story.append(KeepTogether(rows))
    section('Education')
    for entry in p['education']:
        story.extend([Paragraph('<b>' + escape(entry['title']) + '</b>', body), text(entry['organization'] + ' | ' + entry['dates'], small), Spacer(1, 5)])
    section('Projects')
    for project in p['projects']:
        story.append(KeepTogether([Paragraph('<b>' + escape(project['name']) + '</b> | ' + escape(project['status']), body), text(project['description']), Spacer(1, 6)]))
    for repo in draft['analysis'].get('projects', []):
        story.extend([Paragraph('<b>' + escape(repo['name']) + '</b> | Repository evidence to review', body), text(repo.get('description', '')), text(repo['url'], small), Spacer(1, 6)])
    section('Languages'); story.append(text(' | '.join(p['languages'])))
    document.build(story)
    return output.getvalue()
