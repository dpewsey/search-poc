INSERT INTO podcasts (name, slug)
VALUES ('The Yard', 'the-yard')
ON CONFLICT (slug) DO NOTHING;
