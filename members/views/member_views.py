"""
Member CRUD Views - Ultra Compact
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from members.models import Member
from core.models import Company
from datetime import datetime


@login_required
def member_list(request):
    """List all members with search and company filter"""
    search = request.GET.get('search', '').strip()
    company_id = request.GET.get('company_id', '').strip()
    tier = request.GET.get('tier', '').strip()
    page = request.GET.get('page', 1)
    
    # Base queryset
    members = Member.objects.select_related('company')
    
    # Apply search
    if search:
        members = members.filter(
            Q(full_name__icontains=search) |
            Q(member_code__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )
    
    # Apply company filter
    if company_id:
        members = members.filter(company_id=company_id)
    
    # Apply tier filter
    if tier:
        members = members.filter(tier=tier)
    
    # Apply ordering
    members = members.order_by('-joined_date', 'full_name')
    
    # Pagination
    paginator = Paginator(members, 10)
    members_page = paginator.get_page(page)
    
    # Get companies for filter
    companies = Company.objects.filter(is_active=True).order_by('name')
    
    if request.headers.get('HX-Request'):
        return render(request, 'members/member/_table.html', {
            'members': members_page
        })
    
    return render(request, 'members/member/list.html', {
        'members': members_page,
        'search': search,
        'company_id': company_id,
        'tier': tier,
        'companies': companies
    })


@login_required
@require_http_methods(["GET", "POST"])
def member_create(request):
    """Create new member"""
    if request.method == 'POST':
        try:
            company_id = request.POST.get('company_id', '').strip()
            full_name = request.POST.get('full_name', '').strip()
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            birth_date = request.POST.get('birth_date', '').strip()
            gender = request.POST.get('gender', '').strip()
            address = request.POST.get('address', '').strip()
            city = request.POST.get('city', '').strip()
            postal_code = request.POST.get('postal_code', '').strip()
            tier = request.POST.get('tier', 'bronze')
            is_active = request.POST.get('is_active') == 'on'
            
            if not company_id or not full_name or not phone:
                return JsonResponse({
                    'success': False,
                    'message': 'Company, Full Name and Phone are required'
                }, status=400)
            
            # Get company
            company = Company.objects.get(pk=company_id)
            
            # Generate member code
            year_month = datetime.now().strftime('%Y%m')
            last_member = Member.objects.filter(
                company=company,
                member_code__startswith=f'MB-{company.code}-{year_month}'
            ).order_by('-member_code').first()
            
            if last_member:
                last_seq = int(last_member.member_code.split('-')[-1])
                new_seq = last_seq + 1
            else:
                new_seq = 1
            
            member_code = f'MB-{company.code}-{year_month}-{new_seq:04d}'
            
            # Create member
            member_data['created_by'] = request.user
            member = Member.objects.create(
                company=company,
                member_code=member_code,
                full_name=full_name,
                phone=phone,
                email=email,
                birth_date=birth_date if birth_date else None,
                gender=gender,
                address=address,
                city=city,
                postal_code=postal_code,
                tier=tier,
                is_active=is_active,
                created_by=request.user
            )
            
            messages.success(request, f'Member "{member.full_name}" created successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Member created successfully',
                'redirect': '/members/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    companies = Company.objects.filter(is_active=True).order_by('name')
    return render(request, 'members/member/_form.html', {
        'companies': companies
    })


@login_required
@require_http_methods(["GET", "POST"])
def member_update(request, pk):
    """Update existing member"""
    member = get_object_or_404(Member.objects.select_related('company'), pk=pk)
    
    if request.method == 'POST':
        try:
            full_name = request.POST.get('full_name', '').strip()
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            birth_date = request.POST.get('birth_date', '').strip()
            gender = request.POST.get('gender', '').strip()
            address = request.POST.get('address', '').strip()
            city = request.POST.get('city', '').strip()
            postal_code = request.POST.get('postal_code', '').strip()
            tier = request.POST.get('tier', 'bronze')
            is_active = request.POST.get('is_active') == 'on'
            
            if not full_name or not phone:
                return JsonResponse({
                    'success': False,
                    'message': 'Full Name and Phone are required'
                }, status=400)
            
            # Update member
            member.full_name = full_name
            member.phone = phone
            member.email = email
            member.birth_date = birth_date if birth_date else None
            member.gender = gender
            member.address = address
            member.city = city
            member.postal_code = postal_code
            member.tier = tier
            member.is_active = is_active
            member.save()
            
            messages.success(request, f'Member "{member.full_name}" updated successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Member updated successfully',
                'redirect': '/members/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    companies = Company.objects.filter(is_active=True).order_by('name')
    return render(request, 'members/member/_form.html', {
        'member': member,
        'companies': companies
    })


@login_required
@require_http_methods(["POST", "DELETE"])
def member_delete(request, pk):
    """Delete member"""
    try:
        member = get_object_or_404(Member, pk=pk)
        member_name = member.full_name
        member.delete()
        
        messages.success(request, f'Member "{member_name}" deleted successfully!')
        
        return JsonResponse({
            'success': True,
            'message': 'Member deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
