from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

# 1. Cream funcția independentă pentru diacritice
def curata_diacritice(text):
    if not text:
        return ""
        
    inlocuiri = {
        'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ț': 't',
        'Ă': 'A', 'Â': 'A', 'Î': 'I', 'Ș': 'S', 'Ț': 'T',
        'ş': 's', 'ţ': 't', 'Ş': 'S', 'Ţ': 'T' 
    }
    for ro_char, en_char in inlocuiri.items():
        text = text.replace(ro_char, en_char)
        
    return text

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    
    # 2. Apelăm funcția noastră curată pe tot documentul HTML
    html = curata_diacritice(html)

    result = BytesIO()

    # Generare PDF
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None