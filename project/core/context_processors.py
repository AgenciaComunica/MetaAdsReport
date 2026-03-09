from empresas.models import Empresa

from .forms import ActiveCompanyForm


def active_company(request):
    company_id = request.session.get('active_company_id')
    company = None
    if company_id:
        company = Empresa.objects.filter(pk=company_id).first()
    return {
        'active_company': company,
        'companies_for_nav': Empresa.objects.filter(ativo=True).order_by('nome')[:100],
        'active_company_form': ActiveCompanyForm(initial={'empresa': company}),
    }
