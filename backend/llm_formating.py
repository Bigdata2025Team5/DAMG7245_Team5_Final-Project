from bs4 import BeautifulSoup

def convert_itinerary_to_text(html_content: str) -> str:
    """
    Convert HTML itinerary into a clean plain-text summary.
    Keeps headings, key descriptions, bullet lists, activity schedules, and hidden gems section.
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        output_lines = []

        # Extract all day sections (assuming headings for days like <h2>)
        for section in soup.find_all(["h1", "h2", "h3", "p", "li", "strong"]):
            text = section.get_text(strip=True)
            if text:
                output_lines.append(text)

        # Find and specially format the hidden gems section
        hidden_gems_heading = soup.find(string=lambda text: text and "Hidden Gems" in text)
        if hidden_gems_heading:
            # Find the parent element or section containing hidden gems
            parent = None
            for tag in ["h2", "h3", "div"]:
                if hidden_gems_heading.parent.name == tag:
                    parent = hidden_gems_heading.parent
                    break
                    
            if parent:
                # Add separator before hidden gems section
                output_lines.append("\n" + "-" * 40 + "\n")
                output_lines.append("HIDDEN GEMS")
                output_lines.append("-" * 40 + "\n")
                
                # Find all text content in the hidden gems section
                section = parent.find_next_siblings()
                for elem in section:
                    if elem.name in ["p", "li", "div", "span"]:
                        text = elem.get_text(strip=True)
                        if text:
                            output_lines.append(text)

        # Final text blob
        text_output = "\n".join(output_lines)

        return text_output.strip()

    except Exception as e:
        print(f"⚠️ Error parsing HTML to text: {e}")
        return "Unable to extract text from itinerary."