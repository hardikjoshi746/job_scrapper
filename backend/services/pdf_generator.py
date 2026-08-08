from weasyprint import HTML


def generate_pdf(html_content: str, output_path: str) -> str:
    # Claude returns the complete HTML — pass it directly to WeasyPrint
    HTML(string=html_content).write_pdf(output_path)
    return output_path