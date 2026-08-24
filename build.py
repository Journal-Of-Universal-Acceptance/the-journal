from pathlib import Path
from html import escape
from datetime import datetime
import re
import shutil


ROOT = Path(__file__).parent
ARTICLES_DIR = ROOT / "articles"
TEMPLATES_DIR = ROOT / "templates"
SITE_DIR = ROOT / "_site"


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def parse_front_matter(text):
    """
    Reads the YAML-like metadata at the top of an article.
    This intentionally supports the small subset we need.
    """

    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)

    if len(parts) != 3:
        return {}, text

    raw_metadata = parts[1].strip()
    content = parts[2].strip()

    metadata = {}

    for line in raw_metadata.splitlines():

        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        key = key.strip()
        value = value.strip()

        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]

        metadata[key] = value

    return metadata, content


def markdown_to_html(markdown):
    """
    Small Markdown converter for the journal.
    Supports:
      - headings
      - paragraphs
      - bullet lists
      - blockquotes
      - emphasis
      - bold
    """

    lines = markdown.splitlines()

    output = []

    in_list = False

    paragraph = []

    def flush_paragraph():

        nonlocal paragraph

        if not paragraph:
            return

        text = " ".join(
            line.strip()
            for line in paragraph
        )

        text = escape(text)

        text = re.sub(
            r"\*\*(.+?)\*\*",
            r"<strong>\\1</strong>",
            text
        )

        text = re.sub(
            r"\*(.+?)\*",
            r"<em>\\1</em>",
            text
        )

        output.append(
            f"<p>{text}</p>"
        )

        paragraph = []

    for line in lines:

        stripped = line.strip()

        # Blank line
        if not stripped:

            if in_list:
                output.append("</ul>")
                in_list = False

            flush_paragraph()

            continue

        # Heading
        heading = re.match(
            r"^(#{1,6})\s+(.+)$",
            stripped
        )

        if heading:

            if in_list:
                output.append("</ul>")
                in_list = False

            flush_paragraph()

            level = len(heading.group(1))
            text = escape(heading.group(2))

            output.append(
                f"<h{level}>{text}</h{level}>"
            )

            continue

        # Bullet
        bullet = re.match(
            r"^[-*]\s+(.+)$",
            stripped
        )

        if bullet:

            flush_paragraph()

            if not in_list:
                output.append("<ul>")
                in_list = True

            text = escape(bullet.group(1))

            output.append(
                f"<li>{text}</li>"
            )

            continue

        # Blockquote
        if stripped.startswith(">"):

            flush_paragraph()

            text = stripped[1:].strip()

            output.append(
                f"<blockquote>{escape(text)}</blockquote>"
            )

            continue

        paragraph.append(stripped)

    if in_list:
        output.append("</ul>")

    flush_paragraph()

    return "\n".join(output)


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

    return text.strip("-")


def read_articles():

    articles = []

    for path in ARTICLES_DIR.glob("*.md"):

        text = path.read_text(
            encoding="utf-8"
        )

        metadata, markdown = parse_front_matter(text)

        if not metadata.get("title"):
            print(
                f"Skipping {path}: no title"
            )
            continue

        date_string = metadata.get(
            "date",
            "1900-01-01"
        )

        try:
            date = datetime.strptime(
                date_string,
                "%Y-%m-%d"
            )

        except ValueError:

            print(
                f"Invalid date in {path}: "
                f"{date_string}"
            )

            date = datetime(1900, 1, 1)

        article = {
            "source": path,
            "slug": slugify(
                metadata["title"]
            ),
            "title": metadata["title"],
            "author": metadata.get(
                "author",
                "The Editorial Board"
            ),
            "date": date,
            "date_display": date.strftime(
                "%d %B %Y"
            ),
            "type": metadata.get(
                "type",
                "Article"
            ),
            "abstract": metadata.get(
                "abstract",
                ""
            ),
            "content": markdown_to_html(
                markdown
            ),
        }

        articles.append(article)

    articles.sort(
        key=lambda article: article["date"],
        reverse=True
    )

    return articles


def load_template(name):

    path = TEMPLATES_DIR / name

    return path.read_text(
        encoding="utf-8"
    )


def write(path, content):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        content,
        encoding="utf-8"
    )


# --------------------------------------------------
# HTML COMPONENTS
# --------------------------------------------------

def header(active):

    links = [
        ("Home", "index.html", "home"),
        ("Articles", "articles.html", "articles"),
        ("Submit", "submit.html", "submit"),
        ("About", "about.html", "about"),
    ]

    nav = ""

    for label, url, key in links:

        class_name = (
            "active"
            if active == key
            else ""
        )

        nav += (
            f'<a class="{class_name}" '
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
      {nav}
    </nav>

  </div>

</header>
"""


def footer():

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


def page(title, body, active):

    return f"""<!DOCTYPE html>

<html lang="en">

<head>

  <meta charset="UTF-8">

  <meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
  >

  <title>
    {escape(title)} | The Journal of Universal Acceptance
  </title>

  <meta
    name="description"
    content="The Journal of Universal Acceptance"
  >

  <link rel="stylesheet" href="style.css">

</head>

<body>

{header(active)}

<main>

{body}

</main>

{footer()}

</body>

</html>
"""


# --------------------------------------------------
# ARTICLE CARDS
# --------------------------------------------------

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
    {article["date_display"]}
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


# --------------------------------------------------
# BUILD HOMEPAGE
# --------------------------------------------------

def build_homepage(articles):

    latest = articles[:3]

    cards = "\n".join(
        article_card(article)
        for article in latest
    )

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

    html = page(
        "Home",
        body,
        "home"
    )

    write(
        SITE_DIR / "index.html",
        html
    )


# --------------------------------------------------
# BUILD ARTICLE ARCHIVE
# --------------------------------------------------

def build_article_index(articles):

    cards = "\n".join(
        article_card(article)
        for article in articles
    )

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

    html = page(
        "Articles",
        body,
        "articles"
    )

    write(
        SITE_DIR / "articles.html",
        html
    )


# --------------------------------------------------
# BUILD INDIVIDUAL ARTICLES
# --------------------------------------------------

def build_articles(articles):

    template = load_template(
        "article.html"
    )

    for article in articles:

        content = template

        replacements = {
            "{{TITLE}}": escape(
                article["title"]
            ),
            "{{AUTHOR}}": escape(
                article["author"]
            ),
            "{{DATE}}": article[
                "date_display"
            ],
            "{{TYPE}}": escape(
                article["type"]
            ),
            "{{ABSTRACT}}": escape(
                article["abstract"]
            ),
            "{{CONTENT}}": article[
                "content"
            ],
        }

        for key, value in replacements.items():
            content = content.replace(
                key,
                value
            )

        write(
            SITE_DIR
            / "articles"
            / f'{article["slug"]}.html',
            content
        )


# --------------------------------------------------
# COPY STATIC FILES
# --------------------------------------------------

def copy_static_files():

    shutil.copy2(
        ROOT / "style.css",
        SITE_DIR / "style.css"
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)

    SITE_DIR.mkdir()

    articles = read_articles()

    print(
        f"Found {len(articles)} article(s)."
    )

    build_homepage(articles)

    build_article_index(articles)

    build_articles(articles)

    copy_static_files()

    # Copy about and submit templates
    for name, title, active in [
        (
            "about.html",
            "About",
            "about"
        ),
        (
            "submit.html",
            "Submit",
            "submit"
        ),
    ]:

        template = load_template(name)

        html = page(
            title,
            template,
            active
        )

        write(
            SITE_DIR / name,
            html
        )

    print("Build complete.")


if __name__ == "__main__":
    main()
