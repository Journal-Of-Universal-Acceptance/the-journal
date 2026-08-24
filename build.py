from pathlib import Path
from html import escape
from datetime import datetime
import hashlib
import re
import shutil


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).parent

ARTICLES_DIR = ROOT / "articles"
TEMPLATES_DIR = ROOT / "templates"
SITE_DIR = ROOT / "_site"

SITE_TITLE = "The Journal of Universal Acceptance"


# ============================================================
# FILE HELPERS
# ============================================================

def write_file(path, content):
    """Write text to a file, creating directories as needed."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        content,
        encoding="utf-8"
    )


def load_template(filename):
    """Load a template from the templates directory."""

    path = TEMPLATES_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Missing template: {path}"
        )

    return path.read_text(
        encoding="utf-8"
    )


# ============================================================
# FRONT MATTER
# ============================================================

def parse_front_matter(text):
    """
    Read metadata from the beginning of a Markdown article.

    Example:

    ---
    title: "Article Title"
    author: "Author Name"
    date: "2026-08-24"
    type: "Research Article"
    abstract: "Short description."
    submitted: "2026-08-20"
    accepted: "2026-08-24"
    keywords:
      - First Keyword
      - Second Keyword
    ---

    Article content goes here.
    """

    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)

    if len(parts) != 3:
        return {}, text

    metadata_text = parts[1].strip()
    content = parts[2].strip()

    metadata = {}

    lines = metadata_text.splitlines()

    current_key = None

    for line in lines:

        stripped = line.strip()

        if not stripped:
            continue

        # YAML-style keyword list
        if stripped.startswith("- ") and current_key == "keywords":

            keyword = stripped[2:].strip()

            if (
                len(keyword) >= 2
                and keyword.startswith('"')
                and keyword.endswith('"')
            ):
                keyword = keyword[1:-1]

            if "keywords" not in metadata:
                metadata["keywords"] = []

            metadata["keywords"].append(keyword)

            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        key = key.strip()
        value = value.strip()

        current_key = key

        if (
            len(value) >= 2
            and value.startswith('"')
            and value.endswith('"')
        ):
            value = value[1:-1]

        if key == "keywords" and not value:

            metadata[key] = []

        else:

            metadata[key] = value

    return metadata, content


# ============================================================
# MARKDOWN
# ============================================================

def inline_markdown(text):
    """Convert basic inline Markdown to HTML."""

    text = escape(text)

    text = re.sub(
        r"`(.+?)`",
        r"<code>\1</code>",
        text
    )

    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<strong>\1</strong>",
        text
    )

    text = re.sub(
        r"\*(.+?)\*",
        r"<em>\1</em>",
        text
    )

    return text


def markdown_to_html(markdown):
    """
    Convert basic Markdown to HTML.

    Supported:

    # Heading
    ## Heading
    ### Heading

    Paragraphs

    - Lists
    * Lists

    > Blockquotes

    **bold**
    *italic*
    `code`
    """

    lines = markdown.splitlines()

    output = []

    paragraph = []
    in_list = False

    def close_list():
        nonlocal in_list

        if in_list:
            output.append("</ul>")
            in_list = False

    def flush_paragraph():
        nonlocal paragraph

        if not paragraph:
            return

        text = " ".join(
            line.strip()
            for line in paragraph
        )

        output.append(
            f"<p>{inline_markdown(text)}</p>"
        )

        paragraph = []

    for line in lines:

        stripped = line.strip()

        # Blank line
        if not stripped:

            flush_paragraph()
            close_list()

            continue

        # Headings
        heading_match = re.match(
            r"^(#{1,6})\s+(.+)$",
            stripped
        )

        if heading_match:

            flush_paragraph()
            close_list()

            level = len(
                heading_match.group(1)
            )

            heading_text = inline_markdown(
                heading_match.group(2)
            )

            output.append(
                f"<h{level}>{heading_text}</h{level}>"
            )

            continue

        # Bullet lists
        list_match = re.match(
            r"^[-*]\s+(.+)$",
            stripped
        )

        if list_match:

            flush_paragraph()

            if not in_list:
                output.append("<ul>")
                in_list = True

            item = inline_markdown(
                list_match.group(1)
            )

            output.append(
                f"<li>{item}</li>"
            )

            continue

        # Blockquotes
        if stripped.startswith(">"):

            flush_paragraph()
            close_list()

            quote = stripped[1:].strip()

            output.append(
                "<blockquote>"
                f"{inline_markdown(quote)}"
                "</blockquote>"
            )

            continue

        # Normal paragraph
        paragraph.append(stripped)

    flush_paragraph()
    close_list()

    return "\n".join(output)


# ============================================================
# SLUG GENERATION
# ============================================================

def slugify(text):
    """Turn a title into a URL-friendly slug."""

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9\s-]",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        "-",
        text
    )

    text = re.sub(
        r"-+",
        "-",
        text
    )

    return text.strip("-")


# ============================================================
# DATE HELPERS
# ============================================================

def parse_date(value, path, field_name):
    """Parse a YYYY-MM-DD date."""

    try:

        return datetime.strptime(
            value,
            "%Y-%m-%d"
        )

    except ValueError:

        raise ValueError(
            f"Invalid {field_name} date in {path}. "
            f"Use YYYY-MM-DD."
        )


def format_date(date):
    """Format a date for display."""

    return date.strftime(
        "%d %B %Y"
    )


# ============================================================
# PUBLICATION SYSTEM
# ============================================================

def get_publication_info(date):
    """
    Calculate the journal volume and issue from an article date.

    Each volume runs from August through July.

    Each volume contains six bimonthly issues:

        Issue 1: August – September
        Issue 2: October – November
        Issue 3: December – January
        Issue 4: February – March
        Issue 5: April – May
        Issue 6: June – July

    Volume 1 begins in August 2026.
    """

    year = date.year
    month = date.month

    if month >= 8:
        publication_year = year
    else:
        publication_year = year - 1

    volume = publication_year - 2025

    issue = ((month - 8) % 12) // 2 + 1

    issue_periods = {
        1: "August – September",
        2: "October – November",
        3: "December – January",
        4: "February – March",
        5: "April – May",
        6: "June – July",
    }

    return {
        "volume": volume,
        "issue": issue,
        "volume_label": f"Volume {volume}",
        "issue_label": f"Issue {issue}",
        "volume_issue": f"Volume {volume}, Issue {issue}",
        "issue_period": issue_periods[issue],
    }


# ============================================================
# DOI
# ============================================================

def generate_doi(title, date):
    """
    Generate a stable fictional DOI.

    The DOI is deterministic: the same article title and date
    will always produce the same DOI.

    These are intentionally fictional and are NOT registered DOIs.
    """

    source = (
        f"{date.strftime('%Y-%m-%d')}:{title}"
    )

    digest = hashlib.sha1(
        source.encode("utf-8")
    ).hexdigest()[:6]

    return (
        f"10.0000/jua."
        f"{date.year}."
        f"{digest}"
    )


# ============================================================
# READ ARTICLES
# ============================================================

def read_articles():

    articles = []

    if not ARTICLES_DIR.exists():

        print(
            "WARNING: articles directory does not exist."
        )

        return articles

    article_files = sorted(
        ARTICLES_DIR.glob("*.md")
    )

    for path in article_files:

        print(
            f"Reading article: {path}"
        )

        text = path.read_text(
            encoding="utf-8"
        )

        metadata, markdown = parse_front_matter(
            text
        )

        # ----------------------------------------------------
        # Validate metadata
        # ----------------------------------------------------

        required_fields = [
            "title",
            "author",
            "date",
            "type",
            "abstract",
        ]

        missing = [
            field
            for field in required_fields
            if not metadata.get(field)
        ]

        if missing:

            raise ValueError(
                f"Article is missing required metadata: "
                f"{path}\n"
                f"Missing: {', '.join(missing)}"
            )

        # ----------------------------------------------------
        # Publication date
        # ----------------------------------------------------

        date = parse_date(
            metadata["date"],
            path,
            "publication"
        )

        # ----------------------------------------------------
        # Submission date
        # ----------------------------------------------------

        submitted_value = metadata.get(
            "submitted"
        )

        if submitted_value:

            submitted_date = parse_date(
                submitted_value,
                path,
                "submitted"
            )

        else:

            submitted_date = date

        # ----------------------------------------------------
        # Acceptance date
        # ----------------------------------------------------

        accepted_value = metadata.get(
            "accepted"
        )

        if accepted_value:

            accepted_date = parse_date(
                accepted_value,
                path,
                "accepted"
            )

        else:

            accepted_date = date

        # ----------------------------------------------------
        # Keywords
        # ----------------------------------------------------

        keywords = metadata.get(
            "keywords",
            []
        )

        if isinstance(keywords, str):

            keywords = [
                keyword.strip()
                for keyword in keywords.split(",")
                if keyword.strip()
            ]

        if not keywords:

            keywords = [
                "Universal Acceptance"
            ]

        # ----------------------------------------------------
        # Slug
        # ----------------------------------------------------

        slug = slugify(
            metadata["title"]
        )

        if not slug:

            raise ValueError(
                f"Could not create URL slug for: {path}"
            )

        # ----------------------------------------------------
        # Publication information
        # ----------------------------------------------------

        publication = get_publication_info(
            date
        )

        # ----------------------------------------------------
        # DOI
        # ----------------------------------------------------

        doi = generate_doi(
            metadata["title"],
            date
        )

        # ----------------------------------------------------
        # Store article
        # ----------------------------------------------------

        articles.append(
            {
                "source": path,
                "slug": slug,
                "title": metadata["title"],
                "author": metadata["author"],
                "date": date,
                "date_display": format_date(date),

                "submitted_date": submitted_date,
                "submitted_display": format_date(
                    submitted_date
                ),

                "accepted_date": accepted_date,
                "accepted_display": format_date(
                    accepted_date
                ),

                "type": metadata["type"],
                "abstract": metadata["abstract"],
                "keywords": keywords,

                "volume": publication["volume"],
                "issue": publication["issue"],
                "volume_label": publication["volume_label"],
                "issue_label": publication["issue_label"],
                "volume_issue": publication["volume_issue"],
                "issue_period": publication["issue_period"],

                "doi": doi,

                "content": markdown_to_html(
                    markdown
                ),
            }
        )

    # --------------------------------------------------------
    # Newest first
    # --------------------------------------------------------

    articles.sort(
        key=lambda article: article["date"],
        reverse=True
    )

    print(
        f"Found {len(articles)} article(s)."
    )

    return articles


# ============================================================
# HEADER
# ============================================================

def site_header(active, prefix=""):

    links = [
        ("Home", "index.html", "home"),
        ("Articles", "articles.html", "articles"),
        ("Submit", "submit.html", "submit"),
        ("About", "about.html", "about"),
    ]

    navigation = []

    for label, url, key in links:

        active_class = (
            "active"
            if active == key
            else ""
        )

        navigation.append(
            f'<a class="{active_class}" '
            f'href="{prefix}{url}">'
            f'{label}'
            f'</a>'
        )

    return f"""
<header class="site-header">

  <div class="container header-inner">

    <a href="{prefix}index.html" class="brand">

      <span class="brand-abbreviation">
        JUA
      </span>

      <span class="brand-name">

        <strong>
          The Journal of Universal Acceptance
        </strong>

        <small>
          An Open-Access Multidisciplinary Journal
        </small>

      </span>

    </a>

    <nav class="main-nav">

      {"".join(navigation)}

    </nav>

  </div>

</header>
"""


# ============================================================
# FOOTER
# ============================================================

def site_footer(prefix=""):

    return f"""
<footer class="site-footer">

  <div class="container footer-inner">

    <div>

      <strong>
        {SITE_TITLE}
      </strong>

      <p>
        Open access. Open submissions. Open-minded.
      </p>

    </div>

    <div class="footer-links">

      <a href="{prefix}index.html">
        Home
      </a>

      <a href="{prefix}articles.html">
        Articles
      </a>

      <a href="{prefix}submit.html">
        Submit
      </a>

      <a href="{prefix}about.html">
        About
      </a>

    </div>

  </div>

</footer>
"""


# ============================================================
# PAGE WRAPPER
# ============================================================

def make_page(title, body, active, prefix=""):

    return f"""<!DOCTYPE html>

<html lang="en">

<head>

  <meta charset="UTF-8">

  <meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
  >

  <title>
    {escape(title)}
    | {SITE_TITLE}
  </title>

  <meta
    name="description"
    content="{SITE_TITLE}"
  >

  <link
    rel="stylesheet"
    href="{prefix}style.css"
  >

</head>

<body>

{site_header(active, prefix)}

<main>

{body}

</main>

{site_footer(prefix)}

</body>

</html>
"""


# ============================================================
# ARTICLE CARDS
# ============================================================

def article_card(article):

    return f"""
<article class="article-card">

  <div class="article-type">
    {escape(article["type"])}
  </div>

  <h3>
    {escape(article["title"])}
  </h3>

  <p class="article-author">
    {escape(article["author"])}
  </p>

  <p class="article-date">
    {escape(article["date_display"])}
  </p>

  <p class="article-description">
    {escape(article["abstract"])}
  </p>

  <a
    href="articles/{article["slug"]}.html"
    class="read-link"
  >
    Read article →
  </a>

</article>
"""


# ============================================================
# HOMEPAGE
# ============================================================

def build_homepage(articles):

    latest = articles[:3]

    if latest:

        cards = "\n".join(
            article_card(article)
            for article in latest
        )

    else:

        cards = """
<p>
  No articles have been published yet.
</p>
"""

    if articles:

        latest_publication = articles[0]

        volume_label = latest_publication["volume_label"]
        issue_label = latest_publication["issue_label"]

    else:

        volume_label = "Volume 1"
        issue_label = "Issue 1"

    body = f"""
<section class="journal-banner">

  <div class="container">

    <p class="journal-meta">
      ISSN: Pending
      &nbsp; | &nbsp;
      ESTABLISHED 2026
      &nbsp; | &nbsp;
      OPEN ACCESS
    </p>

    <h1>
      The Journal of Universal Acceptance
    </h1>

    <p class="journal-subtitle">
      A multidisciplinary journal dedicated to the
      publication and preservation of submitted knowledge.
    </p>

  </div>

</section>


<section class="container content-section">

  <div class="section-header">

    <div>

      <p class="section-label">
        LATEST ARTICLES
      </p>

      <h2>
        {volume_label}, {issue_label}
      </h2>

    </div>

    <a
      href="articles.html"
      class="text-link"
    >
      View all articles →
    </a>

  </div>


  <div class="article-grid">

    {cards}

  </div>

</section>


<section class="submission-banner">

  <div class="container submission-banner-inner">

    <div>

      <p class="section-label">
        SUBMISSIONS
      </p>

      <h2>
        Have something to contribute?
      </h2>

      <p>
        The Journal of Universal Acceptance welcomes
        submissions from all disciplines and perspectives.
      </p>

    </div>

    <a
      href="submit.html"
      class="button"
    >
      Submit your work
    </a>

  </div>

</section>
"""

    write_file(
        SITE_DIR / "index.html",
        make_page(
            "Home",
            body,
            "home",
            ""
        )
    )


# ============================================================
# ARTICLE ARCHIVE
# ============================================================

def build_article_index(articles):

    if articles:

        cards = "\n".join(
            article_card(article)
            for article in articles
        )

    else:

        cards = """
<p>
  No articles have been published yet.
</p>
"""

    body = f"""
<section class="container page-content">

  <p class="section-label">
    ARTICLE ARCHIVE
  </p>

  <h1 class="page-title">
    All Articles
  </h1>

  <p class="page-introduction">
    Published contributions to The Journal of Universal Acceptance,
    presented in reverse chronological order.
  </p>

  <div class="article-grid">

    {cards}

  </div>

</section>
"""

    write_file(
        SITE_DIR / "articles.html",
        make_page(
            "Articles",
            body,
            "articles",
            ""
        )
    )


# ============================================================
# INDIVIDUAL ARTICLE PAGES
# ============================================================

def build_article_pages(articles):

    template = load_template(
        "article.html"
    )

    for article in articles:

        keyword_html = "\n".join(
            f'<span>{escape(keyword)}</span>'
            for keyword in article["keywords"]
        )

        html = template

        replacements = {

            "{{TITLE}}": escape(
                article["title"]
            ),

            "{{AUTHOR}}": escape(
                article["author"]
            ),

            "{{DATE}}": escape(
                article["date_display"]
            ),

            "{{TYPE}}": escape(
                article["type"]
            ),

            "{{ABSTRACT}}": escape(
                article["abstract"]
            ),

            "{{SUBMITTED}}": escape(
                article["submitted_display"]
            ),

            "{{ACCEPTED}}": escape(
                article["accepted_display"]
            ),

            "{{KEYWORDS}}": keyword_html,

            "{{DOI}}": escape(
                article["doi"]
            ),

            "{{CONTENT}}": article["content"],
        }

        for placeholder, value in replacements.items():

            html = html.replace(
                placeholder,
                value
            )

        html = make_page(
            article["title"],
            html,
            "articles",
            "../"
        )

        article_path = (
            SITE_DIR
            / "articles"
            / f'{article["slug"]}.html'
        )

        write_file(
            article_path,
            html
        )

        print(
            f"Created: {article_path}"
        )


# ============================================================
# STATIC PAGES
# ============================================================

def build_static_page(
    template_name,
    output_name,
    title,
    active
):

    body = load_template(
        template_name
    )

    html = make_page(
        title,
        body,
        active,
        ""
    )

    write_file(
        SITE_DIR / output_name,
        html
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("")
    print("=" * 60)
    print("THE JOURNAL OF UNIVERSAL ACCEPTANCE")
    print("Building site...")
    print("=" * 60)
    print("")

    # --------------------------------------------------------
    # Clean old build
    # --------------------------------------------------------

    if SITE_DIR.exists():

        print(
            "Cleaning old _site directory..."
        )

        shutil.rmtree(
            SITE_DIR
        )

    SITE_DIR.mkdir(
        parents=True
    )

    # --------------------------------------------------------
    # Read articles
    # --------------------------------------------------------

    articles = read_articles()

    # --------------------------------------------------------
    # Build homepage
    # --------------------------------------------------------

    print("")
    print("Building homepage...")

    build_homepage(
        articles
    )

    # --------------------------------------------------------
    # Build article archive
    # --------------------------------------------------------

    print(
        "Building article archive..."
    )

    build_article_index(
        articles
    )

    # --------------------------------------------------------
    # Build individual articles
    # --------------------------------------------------------

    print(
        "Building individual articles..."
    )

    build_article_pages(
        articles
    )

    # --------------------------------------------------------
    # Build About
    # --------------------------------------------------------

    print(
        "Building About page..."
    )

    build_static_page(
        "about.html",
        "about.html",
        "About",
        "about"
    )

    # --------------------------------------------------------
    # Build Submit
    # --------------------------------------------------------

    print(
        "Building Submit page..."
    )

    build_static_page(
        "submit.html",
        "submit.html",
        "Submit",
        "submit"
    )

    # --------------------------------------------------------
    # Build Editorial Board
    # --------------------------------------------------------

    editorial_template = (
        TEMPLATES_DIR
        / "editorial-board.html"
    )

    if editorial_template.exists():

        print(
            "Building Editorial Board page..."
        )

        build_static_page(
            "editorial-board.html",
            "editorial-board.html",
            "Editorial Board",
            "about"
        )

    # --------------------------------------------------------
    # Copy CSS
    # --------------------------------------------------------

    print(
        "Copying stylesheet..."
    )

    shutil.copy2(
        ROOT / "style.css",
        SITE_DIR / "style.css"
    )

    # --------------------------------------------------------
    # Done
    # --------------------------------------------------------

    print("")
    print("=" * 60)
    print(
        f"BUILD SUCCESSFUL — {len(articles)} article(s)"
    )
    print("=" * 60)
    print("")


if __name__ == "__main__":
    main()
