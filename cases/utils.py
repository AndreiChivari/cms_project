from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    
    # SOLUȚIA SIMPLĂ: Înlocuim diacriticele cu litere normale direct în HTML
    inlocuiri = {
        'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ț': 't',
        'Ă': 'A', 'Â': 'A', 'Î': 'I', 'Ș': 'S', 'Ț': 'T',
        'ş': 's', 'ţ': 't', 'Ş': 'S', 'Ţ': 'T'  # Aici am adăugat "vinovații" vechi!
    }
    for ro_char, en_char in inlocuiri.items():
        html = html.replace(ro_char, en_char)

    result = BytesIO()

    # Generăm PDF-ul simplu, fără niciun callback sau font extern!
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None