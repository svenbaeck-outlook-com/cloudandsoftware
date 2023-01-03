    
from jinja2 import Environment, FileSystemLoader
import sys
import xml.etree.ElementTree as ET
import argparse
import os
from datetime import datetime
import re
import base64

POSTS_WIP_FOLDER = "posts_wip"
POSTS_PUBLISH_FOLDER = "posts"

def encode_string(s):
    cs = ''
    for i in s:
        cs += "%03d" % ord(i)
    return cs

def decode_string(s):
    ds = ''
    for i in range(int(len(s)/3)):
        a = s[i*3:i*3+3]
        ds += chr(int(a))
    return ds

def init_template():
    environment = Environment(loader=FileSystemLoader("tooling/"))
    template = environment.get_template("blog_template.jinja")
    return template

def argument_parsing():
    parser = argparse.ArgumentParser(
                    prog = 'cspublish',
                    description = 'Automate cloud and software blog posts',
                    epilog = 'Simplifying blogging')
    sub_parsers = parser.add_subparsers(dest='command')

    generate_parser = sub_parsers.add_parser('generate')
    generate_parser.add_argument('-t', '--title', action='store', required=True)
    generate_parser.add_argument('-s', '--subtitle', action='store', required=True)
    generate_parser.add_argument('-c', '--technology', action='store', required=True, choices=['cloud','azure','aws','gcp','python','powershell','windows','linux','software','infra as code'])
    
    publish_parser = sub_parsers.add_parser('publish')
    publish_parser.add_argument('-f', '--file', action='store', required=True)

    try:
        args = parser.parse_args()
    except argparse.ArgumentError as e:
        print ("Argument parsing error: %s", str(e))
        parser.print_help()
        exit

    if (args.command == 'generate'):
        generate_blog_post(args.title, args.subtitle, args.technology)

    if (args.command == 'publish'):
        publish_blog_post(args.file)

    return  

class blog_post():
    def __init__(self, title, subtitle, publish_date, formatted_publish_date, link):
        self.title = title
        self.subtitle = subtitle
        self.publish_date = publish_date
        self.formatted_publish_date = formatted_publish_date
        self.link = link

def publish_blog_post(filename):
    if (not os.path.exists(filename)):
        print(f"Error: Blog post '{filename}' doesn't exist!")
        exit()
    
    post_folder = os.path.dirname(os.path.abspath(filename))

    if (post_folder != os.path.join(os.path.dirname(__file__), POSTS_WIP_FOLDER)):
        print(f"Error: Blog post '{filename}' is not in the correct folder!")
        exit()

    start_name = os.path.splitext(os.path.basename(filename))[0]
    for f in os.listdir(os.path.join(os.path.dirname(__file__), POSTS_PUBLISH_FOLDER)):
        if f.startswith(start_name):
            print(f"Error: A blog with the same title already exists for {filename}")
            exit()
    
    environment = Environment(loader=FileSystemLoader(post_folder))
    template = environment.get_template(os.path.basename(filename))

    current_datetime = datetime.now()
    current_year = current_datetime.strftime("%Y")
    post_date = current_datetime.strftime("%B %d, %Y")

    content = template.render(postdate = post_date, year = current_year)

    short_file_name = os.path.splitext(os.path.split(filename)[1])
    short_file_name = "%s___%s%s" % (short_file_name[0], encode_string(str(current_datetime.timestamp())), short_file_name[1])
    output_filename = os.path.join(os.path.dirname(__file__), POSTS_PUBLISH_FOLDER, short_file_name)

    with open(output_filename, mode="w", encoding="utf-8") as message:
        message.write(content)
        print(f"The blog post is available at {output_filename}")

    # Generate the index file

    blogs = []
    for f in os.listdir(os.path.join(os.path.dirname(__file__), POSTS_PUBLISH_FOLDER)):
        full_name = os.path.join(os.path.dirname(__file__), POSTS_PUBLISH_FOLDER, f)
        with(open(full_name, mode="r") as fl):
            # Get title and subtitle from the content
            content = fl.read()
            m = re.findall("<h1>(.+)</h1>", content)
            if len(m) == 0:
                print(r"Error: no title found for blog {filename}")
                exit
            if (len(m) > 1):
                print(r"Error: The H1 tag must not be used in a blog article in {filename}")
                exit
            title = m[0]

            m = re.findall("<span class=\"subheading\">(.+)</span>", content)
            if len(m) == 0:
                print(r"Error: No subheading found for blog {filename}")
                exit
            if (len(m) > 1):
                print(r"Error: Multiple subheadings found in blog article in {filename}")
                exit
            subtitle = m[0]

            publish_date = float(decode_string(os.path.splitext(f.split('___')[1])[0]))
            dt = datetime.fromtimestamp(publish_date).strftime("%B %d, %Y")
            print(dt)

            rel_file = os.path.join(POSTS_PUBLISH_FOLDER, f)

            blogs.append( blog_post(title, subtitle, publish_date, dt, rel_file) )

    # sort blogs from recent to old
    blogs.sort(key=lambda x: x.publish_date, reverse=True)

    print (blogs)

    blog_index_folder = os.path.join(os.path.dirname(__file__), "tooling")
    environment = Environment(loader=FileSystemLoader(blog_index_folder))
    template = environment.get_template("index_template.jinja")
    content = template.render(posts=blogs)

    index_file = os.path.join(os.path.dirname(__file__), 'index.html')
    with open(index_file, mode="w", encoding="utf-8") as message:
        message.write(content)
        print(f"The index is available at {index_file   }")


def generate_blog_post(title, subtitle, technology):
    filename = os.path.join(os.path.dirname(__file__), POSTS_WIP_FOLDER, "post_%s.html" % title.replace(" ", "_").lower())
    if (os.path.exists(filename)):
        print(f"Error: A blog post with the title {title} exists already!")
        exit()

    environment = Environment(loader=FileSystemLoader("tooling/"))
    template = environment.get_template("blog_template.jinja")

    content = template.render(title=title.lower().capitalize(), subtitle=subtitle.lower().capitalize(), technology=technology.lower().capitalize())

    with open(filename, mode="w", encoding="utf-8") as message:
        message.write(content)
        print(f"The blog post skeleton is available at {filename}")

def load_blog_post():
    blog_post_file = sys.argv[1]
    blog_data = ET.parse(blog_post_file)
    root = blog_data.getroot()
    title = root.get('/title')
    subtitle = root.get('/subtitle')
    for item in root.findall('./article/paragraph'):
        
        # empty news dictionary
        paragraphs = []
  
        # iterate child elements of item
        for child in item:
  
            # special checking for namespace object content:media
            if child.tag == '{http://search.yahoo.com/mrss/}content':
                news['media'] = child.attrib['url']
            else:
                news[child.tag] = child.text.encode('utf8')
  
        # append news dictionary to news items list
        newsitems.append(news)
      
argument_parsing()
