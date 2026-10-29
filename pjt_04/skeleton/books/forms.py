from django import forms
from .models import Book

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = '__all__'
        labels = {
            'title': '제목',
            'description': '설명',
            'customer_review_rank': '회원 리뷰 평점',
            'author': '저자',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6}),
            'customer_review_rank': forms.NumberInput(attrs={'step': 0.1, 'min': 0, 'max': 5}),
        }
