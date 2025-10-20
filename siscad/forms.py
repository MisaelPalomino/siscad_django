from django import forms


class UploadExcelForm(forms.Form):
    file = forms.FileField(label="Archivo Excel", help_text="Sube un archivo .xlsx")

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.endswith(".xlsx"):
            raise forms.ValidationError("El archivo debe ser .xlsx")
        return f
