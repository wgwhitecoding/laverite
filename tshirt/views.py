from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import json

from .models import Design, DesignDecal, DesignText

def about_page(request):
    """
    Renders the landing/about page.
    """
    return render(request, 'tshirt/about.html')  # App-specific path

def home(request):
    """
    Renders the create page.
    """
    return render(request, 'tshirt/home.html') 


@csrf_exempt  # Remove this decorator in production for security
def upload_decal(request):
    """
    Endpoint to handle file uploads (multipart/form-data).
    Saves the file in MEDIA_ROOT/decals/ and returns the file URL.
    """
    if request.method == 'POST':
        file_obj = request.FILES.get('decalFile', None)
        if not file_obj:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        # Validate file type
        import imghdr
        file_type = imghdr.what(file_obj)
        if file_type not in ['jpeg', 'png', 'gif', 'bmp']:
            return JsonResponse({'error': 'Invalid file type'}, status=400)

        # Secure the file name
        file_name = default_storage.get_available_name(file_obj.name)
        save_path = os.path.join('decals', file_name)

        # Save the file
        saved_path = default_storage.save(save_path, ContentFile(file_obj.read()))
        file_url = default_storage.url(saved_path)  # e.g., /media/decals/filename.png

        return JsonResponse({'status': 'ok', 'file_url': file_url})

    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt  # Remove this decorator in production for security
def save_design(request):
    """
    POST endpoint to save the user's design data.
    If logged in, saves to the database.
    If anonymous, saves to the session.
    Expects JSON with:
      - product (tshirt, baggy, hoodie, jumper)
      - color (e.g. #ffffff)
      - decals: each with imageUrl, pos, rot, size
      - texts: each with content, color, pos, rot, scale
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Validate essential fields
        product = data.get('product', 'tshirt')
        color = data.get('color', '#ffffff')
        decals = data.get('decals', [])
        texts = data.get('texts', [])

        if product not in dict(Design.PRODUCT_CHOICES):
            return JsonResponse({'error': 'Invalid product choice'}, status=400)

        # If user is authenticated, save to DB
        if request.user.is_authenticated:
            design = Design.objects.create(
                user=request.user,
                product=product,
                color=color
            )

            # Save decals
            for d in decals:
                image_url = d.get('imageUrl', '')
                if not image_url:
                    continue  # Skip decals without imageUrl

                # Convert imageUrl to relative path
                if image_url.startswith('/media/'):
                    image_relative_path = image_url.replace('/media/', '', 1)
                else:
                    image_relative_path = image_url  # Adjust as needed

                # Check if the file exists
                if not default_storage.exists(image_relative_path):
                    continue  # Skip if file doesn't exist

                DesignDecal.objects.create(
                    design=design,
                    image=image_relative_path,
                    pos_x=d.get('position', {}).get('x', 0.0),
                    pos_y=d.get('position', {}).get('y', 0.0),
                    pos_z=d.get('position', {}).get('z', 0.0),
                    rot_x=d.get('rotation', {}).get('x', 0.0),
                    rot_y=d.get('rotation', {}).get('y', 0.0),
                    rot_z=d.get('rotation', {}).get('z', 0.0),
                    size_x=d.get('size', {}).get('x', 0.5),
                    size_y=d.get('size', {}).get('y', 0.5),
                    size_z=d.get('size', {}).get('z', 0.5)
                )

            # Save texts
            for t in texts:
                content = t.get('content', '')
                if not content:
                    continue  # Skip texts without content

                DesignText.objects.create(
                    design=design,
                    content=content,
                    color=t.get('color', '#000000'),
                    pos_x=t.get('position', {}).get('x', 0.0),
                    pos_y=t.get('position', {}).get('y', 0.0),
                    pos_z=t.get('position', {}).get('z', 0.0),
                    rot_x=t.get('rotation', {}).get('x', 0.0),
                    rot_y=t.get('rotation', {}).get('y', 0.0),
                    rot_z=t.get('rotation', {}).get('z', 0.0),
                    scale_x=t.get('scale', {}).get('x', 1.0),
                    scale_y=t.get('scale', {}).get('y', 1.0),
                    scale_z=t.get('scale', {}).get('z', 1.0)
                )

            return JsonResponse({'status': 'ok', 'design_id': design.id})

        else:
            # Anonymous user: save to session
            request.session['temp_design'] = data
            return JsonResponse({'status': 'session_saved'})

    return JsonResponse({'error': 'Invalid request'}, status=400)

def load_design(request):
    """
    GET endpoint to load the user's design.
    If authenticated, loads from DB.
    If anonymous, loads from session.
    Returns JSON with:
      - product
      - color
      - decals: list of decals
      - texts: list of texts
    """
    if request.method == 'GET':
        # If user is authenticated, load the latest design from DB
        if request.user.is_authenticated:
            design = Design.objects.filter(user=request.user).order_by('-created_at').first()
            if not design:
                return JsonResponse({'status': 'no_design', 'error': 'No design found'}, status=200)

            # Prepare JSON data
            data = {
                'product': design.product,
                'color': design.color,
                'decals': [],
                'texts': []
            }

            for decal in design.decals.all():
                data['decals'].append({
                    'imageUrl': decal.image.url if decal.image else '',
                    'position': {'x': decal.pos_x, 'y': decal.pos_y, 'z': decal.pos_z},
                    'rotation': {'x': decal.rot_x, 'y': decal.rot_y, 'z': decal.rot_z},
                    'size': {'x': decal.size_x, 'y': decal.size_y, 'z': decal.size_z},
                    'name': f'Decal {decal.id}'
                })

            for text in design.texts.all():
                data['texts'].append({
                    'content': text.content,
                    'color': text.color,
                    'position': {'x': text.pos_x, 'y': text.pos_y, 'z': text.pos_z},
                    'rotation': {'x': text.rot_x, 'y': text.rot_y, 'z': text.rot_z},
                    'scale': {'x': text.scale_x, 'y': text.scale_y, 'z': text.scale_z},
                    'name': f'Text {text.id}'
                })

            return JsonResponse({'status': 'ok', 'design': data}, status=200)

        else:
            # Anonymous user: load from session
            temp_design = request.session.get('temp_design')
            if not temp_design:
                return JsonResponse({'status': 'no_design', 'error': 'No design in session'}, status=200)

            return JsonResponse({'status': 'ok', 'design': temp_design}, status=200)

    return JsonResponse({'error': 'Invalid request method'}, status=400)







