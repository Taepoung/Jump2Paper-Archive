import os
import re
import glob

KNOWN_LANGS = {
    'kr': 'Korean (KR)',
    'en': 'English (EN)',
    'jp': 'Japanese (JP)',
    'cn': 'Chinese (CN)',
    'fr': 'French (FR)',
    'de': 'German (DE)',
    'es': 'Spanish (ES)'
}

def get_html_title(filepath):
    """Extracts the title from an HTML file, or returns formatted filename as a fallback."""
    title = ""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read() 
            # First try to find h1 within p2w-hero div
            match = re.search(r'p2w-hero[^>]*>.*?<h1>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                # Clean up any potential internal tags (like <br>, <span> etc) within h1
                title = re.sub(r'<[^>]+>', '', title)
            else:
                # Fallback to <title> tag
                match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                if match:
                    title = match.group(1).strip()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        
    if title:
        title = re.sub(r'<[^>]+>', '', title)

    if not title:
        # Fallback to filename formatting
        filename = os.path.basename(filepath)
        name_without_ext = os.path.splitext(filename)[0]
        # Replace dashes and underscores with spaces and title case
        title = name_without_ext.replace('-', ' ').replace('_', ' ').title()
    return title

def generate_index():
    # The script is in .github/scripts/, so root is two levels up
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    all_files = []
    active_langs = set()
    
    # 1. Dynamically scan all subdirectories for HTML files
    for entry in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, entry)
        if os.path.isdir(folder_path) and not entry.startswith('.') and entry not in ['node_modules', '__pycache__']:
            html_files = glob.glob(os.path.join(folder_path, '*.html'))
            if html_files:
                active_langs.add(entry)
                for f in html_files:
                    rel_path = os.path.relpath(f, base_dir).replace('\\', '/')
                    title = get_html_title(f)
                    all_files.append({"lang": entry, "path": rel_path, "title": title})
                    
    # Sort files by title
    all_files.sort(key=lambda x: x['title'])
    
    # Sort languages
    active_langs = sorted(list(active_langs))

    # 2. Generate filter buttons dynamically
    filters_html = '<button class="filter-btn active" data-lang="all">All</button>\n'
    for lang in active_langs:
        display_name = KNOWN_LANGS.get(lang.lower(), lang.upper())
        filters_html += f'        <button class="filter-btn" data-lang="{lang}">{display_name}</button>\n'

    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Paper2Web Archive</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=DM+Sans:wght@400;500;600&display=swap');

    :root {{
      --color-bg: #ffffff;
      --color-bg-soft: #f8f7f4;
      --color-text: #1a1a1a;
      --color-text-muted: #6b6b6b;
      --color-accent: #e8601c;
      --color-accent-light: #fdf0e8;
      --color-positive: #2d7d46;
      --color-positive-bg: #edf7f1;
      --color-negative: #c0392b;
      --color-negative-bg: #fdf0ee;
      --color-border: #e0ddd8;

      --font-body: 'Lora', Georgia, serif;
      --font-ui: 'DM Sans', system-ui, sans-serif;

      --text-base: 17px;
      --line-height: 1.8;
      --content-width: 800px;
    }}

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    html {{ font-size: var(--text-base); }}

    body {{
      background: var(--color-bg);
      color: var(--color-text);
      font-family: var(--font-body);
      line-height: var(--line-height);
    }}

    .p2w-content {{ max-width: var(--content-width); margin: 0 auto; padding: 0 2rem; }}

    h1, h2, h3, h4, h5 {{ font-family: var(--font-ui); color: var(--color-text); line-height: 1.3; }}

    .p2w-hero {{
      padding: 5rem 0 3rem;
      border-bottom: 1px solid var(--color-border);
      text-align: center;
    }}
    .p2w-hero h1 {{ font-size: 2.4rem; font-weight: 600; margin-bottom: 1rem; }}
    .p2w-hero p {{ color: var(--color-text-muted); font-size: 1.1rem; }}

    /* 검색 및 필터 파트 */
    .controls-section {{
      padding: 2rem 0;
      border-bottom: 1px solid var(--color-border);
      background: var(--color-bg-soft);
    }}
    .controls-container {{
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      align-items: center;
    }}
    .search-input {{
      width: 100%;
      max-width: 500px;
      padding: 0.8rem 1.2rem;
      font-size: 1rem;
      font-family: var(--font-ui);
      border: 1px solid var(--color-border);
      border-radius: 8px;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }}
    .search-input:focus {{
      border-color: var(--color-accent);
      box-shadow: 0 0 0 3px var(--color-accent-light);
    }}
    .filter-group {{
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      justify-content: center;
    }}
    .filter-btn {{
      font-family: var(--font-ui);
      font-size: 0.9rem;
      padding: 0.4rem 1.2rem;
      border: 1px solid var(--color-border);
      background: var(--color-bg);
      color: var(--color-text-muted);
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .filter-btn:hover {{ border-color: var(--color-accent); color: var(--color-accent); }}
    .filter-btn.active {{
      background: var(--color-accent);
      color: #fff;
      border-color: var(--color-accent);
    }}

    /* 문서 목록 파트 */
    .papers-section {{ padding: 3rem 0; }}
    .paper-list {{ display: flex; flex-direction: column; gap: 1rem; }}
    .paper-card {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.2rem 1.5rem;
      border: 1px solid var(--color-border);
      border-radius: 8px;
      text-decoration: none;
      color: var(--color-text);
      transition: all 0.2s;
      background: var(--color-bg);
    }}
    .paper-card:hover {{
      border-color: var(--color-accent);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    .paper-info h3 {{ font-size: 1.15rem; margin-bottom: 0.3rem; transition: color 0.2s; }}
    .paper-card:hover .paper-info h3 {{ color: var(--color-accent); }}
    
    /* 동적 언어 뱃지 공통 스타일 */
    .lang-badge {{
      font-family: var(--font-ui);
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
      text-transform: uppercase;
      background: var(--color-bg-soft);
      border: 1px solid var(--color-border);
      color: var(--color-text-muted);
    }}
    /* 특수한 언어에만 색상 부여 (나머지는 위 기본값 적용) */
    .lang-badge.kr {{ background: #eef3fb; color: #3a6bbf; border: 1px solid #b8cef0; }}
    .lang-badge.en {{ background: var(--color-positive-bg); color: var(--color-positive); border: 1px solid #b8e0c8; }}
    
    .no-results {{
      text-align: center;
      padding: 3rem 0;
      color: var(--color-text-muted);
      font-family: var(--font-ui);
      display: none;
    }}
  </style>
</head>
<body>

  <div class="p2w-hero">
    <div class="p2w-content">
      <h1>Paper2Web Archive</h1>
      <p>Explore our formatted academic papers.</p>
    </div>
  </div>

  <div class="controls-section">
    <div class="p2w-content controls-container">
      <input type="text" id="searchInput" class="search-input" placeholder="Search papers by title..." autocomplete="off">
      <div class="filter-group" id="filterGroup">
        {filters_html}      </div>
    </div>
  </div>

  <div class="papers-section p2w-content">
    <div class="paper-list" id="papersList">
"""
    
    for item in all_files:
        lang = item['lang']
        display_name = KNOWN_LANGS.get(lang.lower(), lang.upper())
        # If it's something like "Korean (KR)", just extract "Korean" for the card badge
        short_label = display_name.split(' (')[0] if ' (' in display_name else display_name
        
        html_content += f"""
      <a href="{item['path']}" class="paper-card" data-title="{item['title'].lower()}" data-lang="{lang}">
        <div class="paper-info">
          <h3>{item['title']}</h3>
        </div>
        <div class="lang-badge {lang}">{short_label}</div>
      </a>"""
            
    html_content += """
    </div>
    <div id="noResults" class="no-results">
      No papers found matching your criteria.
    </div>
  </div>

  <script>
    const searchInput = document.getElementById('searchInput');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const cards = document.querySelectorAll('.paper-card');
    const noResults = document.getElementById('noResults');
    
    let currentLang = 'all';
    let currentSearch = '';

    function filterPapers() {
      let visibleCount = 0;
      
      cards.forEach(card => {
        const title = card.getAttribute('data-title');
        const lang = card.getAttribute('data-lang');
        
        const matchesSearch = title.includes(currentSearch);
        const matchesLang = currentLang === 'all' || lang === currentLang;
        
        if (matchesSearch && matchesLang) {
          card.style.display = 'flex';
          visibleCount++;
        } else {
          card.style.display = 'none';
        }
      });
      
      noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }

    searchInput.addEventListener('input', (e) => {
      currentSearch = e.target.value.toLowerCase().trim();
      filterPapers();
    });

    filterBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        filterBtns.forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentLang = e.target.getAttribute('data-lang');
        filterPapers();
      });
    });
  </script>
</body>
</html>
"""

    index_path = os.path.join(base_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"✅ Successfully created {index_path} with {len(all_files)} papers across {len(active_langs)} languages.")

if __name__ == "__main__":
    generate_index()
