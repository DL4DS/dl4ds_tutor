---
title: Chainlit Base
emoji: 🏃
colorFrom: green
colorTo: red
sdk: docker
pinned: false
hf_oauth: true
---

Chainlit Base
===========

To run locally, 

Clone the repository from: https://github.com/DL4DS/dl4ds_tutor    

Change the branch to the `chainlit_base` branch.

Create a `.env` file, view `code/modules/constants.py` for the required environment variables.

Set required args in the `code/config.yml` and `code/modules/constants.py` files. 

Put your data under the `storage/data` directory. Note: You can add urls in the urls.txt file, and other pdf files in the `storage/data` directory.    

> Note: The 'WebpageCrawler' in `code/modules/helpers.py` takes in the urls from the `storage/data/urls.txt` file, and gets all children urls and files from the urls provided. If you want to read only the data in the urls provided, set `["embedding_options"]["expand_urls"]` to False in the `code/config.yaml` file.

To create the Vector Database, run the following command:   
```python code/modules/vector_db.py```    
(Note: You would need to run the above when you add new data to the `storage/data` directory, or if the ``storage/data/urls.txt`` file is updated. Or you can set ``["embedding_options"]["embedd_files"]`` to True in the `code/config.yaml` file, which would embed files from the storage directory everytime you run the below chainlit command.)

To run the chainlit app, run the following command:   
```chainlit run code/main.py```

See below for Docker instructions.

See the [docs](https://github.com/DL4DS/dl4ds_tutor/tree/main/docs) for more information.

## Docker 

The HuggingFace Space is built using the `Dockerfile` in the repository. To run it locally, use the `Dockerfile.dev` file.
1. docker build --tag dev  -f Dockerfile.dev .
2. docker run -it --rm -p 8051:8051 dev    

## Contributing

Please create an issue if you have any suggestions or improvements, and start working on it by creating a branch and by making a pull request to the main branch.
