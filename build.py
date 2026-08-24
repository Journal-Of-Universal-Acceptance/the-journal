from pathlib import Path
from html import escape
from datetime import datetime
import re
import shutil


ROOT = Path(__file__).parent
ARTICLES_DIR = ROOT / "articles"
TEMPLATES_DIR = ROOT / "templates"
SITE_DIR = ROOT / "_site"


# ============================================================
# FRONT MATTER
# ============================================================

def parse_front_matter(text):
    """
    Parse the simple YAML-style metadata at the top of
    each Markdown article.
    """

    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)

    if len(parts) != 3:
        return {}, text

    metadata_text = parts[1].strip()
    content = parts[2].strip()

    metadata = {}

    for line in metadata_text.splitlines():

        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value.startswith('"')
            and value.endswith('"')
        ):
            value = value[1:-1]

        metadata[key] = value

    return metadata, content


# ============================================================
# MARKDOWN
# ============================================================

def inline_markdown(text):
    """
    Convert a small, safe subset of Markdown to HTML.
    """

    text = escape(text)

    # Bold
    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<strong>\1</strong>",
        text
    )

    # Italic
    text = re.sub(
        r"\*(.+?)\*",
        r"<em>\1</em>",
        text
    )

    # Inline code
    text = re.sub(
        r"`(.+?)`",
        r"<code>\1</code>",
        text
    )

    return text


def markdown_to_html(markdown):
    """
    Convert the basic Markdown used by the journal
    into HTML.
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

        # Heading
        match = re.match(
            r"^(#{1,6})\s+(.+)$",
            stripped
        )

        if match:

            flush_paragraph()
            close_list()

            level = len(match.group(1))
            text = inline_markdown(
                match.group(2)
            )

            output.append(
                f"<h{level}>{text}</h{level}>"
            )

            continue

        # Bullet list
        match = re.match(
            r"^[-*]\s+(.+)$",
            stripped
        )

        if match:

            flush_paragraph()

            if not in_list:
                output.append("<ul>")
                in_list = True

            text = inline_markdown(
                match.group(1)
            )

            output.append(
                f"<li>{text}</li>"
            )

            continue

        # Blockquote
        if stripped.startswith(">"):

            flush_paragraph()
            close_list()

            text = stripped[1:].strip()

            output.append(
                f"<blockquote>"
                f"{inline_markdown(text)}"
                f"</blockquote>"
            )

            continue

        # Normal paragraph
        paragraph.append(stripped)

    flush_paragraph()
    close_list()

    return "\n".join(output)


# ============================================================
# SLUGS
# ============================================================

def slugify(text):

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
# ARTICLES
# ============================================================

def read_articles():

    articles = []

    if not ARTICLES_DIR.exists():

        print("No articles directory found.")

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

        if not metadata:

            raise ValueError(
                f"""
Article could not be read:

{path}

Make sure the file begins with:

---
title: "Your Article Title"
author: "Author Name"
date: "2026-08-24"
type: "Article"
abstract: "Short description."
---

"""

            )

        required = [
            "title",
            "author",
            "date",
            "type",
            "abstract",
        ]

        missing = [
            field
            for field in required
            if not metadata.get(field)
        ]

        if missing:

            raise ValueError(
                f"""
Article is missing required metadata:

{path}

Missing:
{", ".join(missing)}

"""

            )

        try:

            date = datetime.strptime(
                metadata["date"],
                "%Y-%m-%d"
            )

        except ValueError:

            raise ValueError(
                f"""
Invalid date in:

{path}

Date must use:

YYYY-MM-DD

Example:

date: "2026-08-24"
"""

            )

        title = metadata["title"]

        slug = slugify(title)

        if not slug:

            raise ValueError(
                f"Could not create URL slug for: {path}"
            )

        articles.append(
            {
                "source": path,
                "slug": slug,
                "title": title,
                "author": metadata["author"],
                "date": date,
                "date_display": date.strftime(
                    "%d %B %Y"
                ),
                "type": metadata["type"],
                "abstract": metadata["abstract"],
                "content": markdown_to_html(
                    markdown
                ),
            }
        )

    # Newest first
    articles.sort(
        key=lambda article: article["date"],
        reverse=True
    )

    print(
        f"Found {len(articles)} article(s)."
    )

    return articles


# ============================================================
# TEMPLATES
# ============================================================

def load_template(filename):

    path = TEMPLATES_DIR / filename

    if not path.exists():

        raise FileNotFoundError(
            f"Missing template: {path}"
        )

    return path.read_text(
        encoding="utf-8"
    )


# ============================================================
# HEADER
# ============================================================

def site_header(active):

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
            f'href="{url}">{label}</a>'
        )

    return f"""
<header class="site-header">

  <div class="container header-inner">

    <a href="index.html" class="brand">

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

def site_footer():

    return """
<footer class="site-footer">

  <div class="container footer-inner">

    <div>

      <strong>
        The Journal of Universal Acceptance
      </strong>

      <p>
        Open access. Open submissions. Open-minded.
      </p>

    </div>

    <div class="footer-links">

      <a href="index.html">Home</a>
      <a href="articles.html">Articles</a>
      <a href="submit.html">Submit</a>
      <a href="about.html">About</a>

    </div>

  </div>

</footer>
"""


# ============================================================
# PAGE WRAPPER
# ============================================================

def make_page(title, body, active):

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
    | The Journal of Universal Acceptance
  </title>

  <meta
    name="description"
    content="The Journal of Universal Acceptance"
  >

  <link rel="stylesheet" href="style.css">

</head>

<body>

{site_header(active)}

<main>

{body}

</main>

{site_footer()}

</body>

</html>
"""


# ============================================================
# ARTICLE CARD
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
        Volume 1, Issue 1
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


<section class="container content-section journal-information">

  <div>

    <p class="section-label">
      ABOUT THE JOURNAL
    </p>

    <h2>
      A commitment to universal publication.
    </h2>

  </div>

  <div>

    <p>
      The Journal of Universal Acceptance is an independent,
      multidisciplinary publication committed to ensuring
      that submitted work receives the opportunity to enter
      the published record.
    </p>

    <a
      href="about.html"
      class="text-link"
    >
      Learn more about the journal →
    </a>

  </div>

</section>
"""

    write_file(
        SITE_DIR / "index.html",
        make_page(
            "Home",
            body,
            "home"
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
            "articles"
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
            "{{CONTENT}}": article["content"],
        }

        for placeholder, value in replacements.items():

            html = html.replace(
                placeholder,
                value
            )

        # Article pages are one directory deeper,
        # so they need the stylesheet one level up.
        html = html.replace(
            'href="style.css"',
            'href="../style.css"'
        )

        html = make_page(
            article["title"],
            html,
            "articles"
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
        active
    )

    write_file(
        SITE_DIR / output_name,
        html
    )


# ============================================================
# FILE WRITING
# ============================================================

def write_file(path, content):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        content,
        encoding="utf-8"
    )


# ============================================================
# MAIN BUILD
# ============================================================

def main():

    print("")
    print("=" * 60)
    print("THE JOURNAL OF UNIVERSAL ACCEPTANCE")
    print("Building site...")
    print("=" * 60)
    print("")

    # Start with a completely clean build directory.
    if SITE_DIR.exists():

        shutil.rmtree(
            SITE_DIR
        )

    SITE_DIR.mkdir(
        parents=True
    )

    # Read articles.
    articles = read_articles()

    # Generate homepage.
    print("Building homepage...")

    build_homepage(
        articles
    )

    # Generate archive.
    print("Building article archive...")

    build_article_index(
        articles
    )

    # Generate individual articles.
    print("Building article pages...")

    build_article_pages(
        articles
    )

    # Generate About page.
    print("Building About page...")

    build_static_page(
        "about.html",
        "about.html",
        "About",
        "about"
    )

    # Generate Submit page.
    print("Building Submit page...")

    build_static_page(
        "submit.html",
        "submit.html",
        "Submit",
        "submit"
    )

    # Copy CSS.
    print("Copying stylesheet...")

    shutil.copy2(
        ROOT / "style.css",
        SITE_DIR / "style.css"
    )

    print("")
    print("=" * 60)
    print(
        f"BUILD SUCCESSFUL — {len(articles)} article(s)"
    )
    print("=" * 60)
    print("")


if __name__ == "__main__":
    main()
