from django import forms

from .models import Thread

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


class ThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ('title', 'content', 'image')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '쓰레드 제목', 'maxlength': 60}),
            'content': forms.Textarea(attrs={'rows': 10, 'maxlength': 2000,
                                             'placeholder': '이 책을 읽고 떠오른 생각을 자유롭게 남겨 보세요.'}),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = 'form-control'
            if self.is_bound and name in self.errors:
                css += ' is-invalid'
            field.widget.attrs['class'] = css

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if len(title) < 2:
            raise forms.ValidationError('제목은 2자 이상 써 주세요.')
        return title

    def clean_content(self):
        content = self.cleaned_data['content'].strip()
        if len(content) < 10:
            raise forms.ValidationError('내용은 10자 이상 써 주세요.')
        return content

    def clean_image(self):
        # ImageField가 Pillow로 실제 이미지인지 먼저 검사하고, 여기서는 크기만 확인한다
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'size') and image.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError('이미지는 5MB 이하만 올릴 수 있어요.')
        return image
